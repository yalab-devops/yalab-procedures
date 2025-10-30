import os
from pathlib import Path
from subprocess import CalledProcessError, run
from typing import Any, Dict

from nipype.interfaces.base import (
    CommandLine,
    CommandLineInputSpec,
    Directory,
    File,
    isdefined,
    traits,
)

from yalab_procedures.procedures.base.procedure import (
    Procedure,
    ProcedureInputSpec,
    ProcedureOutputSpec,
)


class QsireconInputSpec(ProcedureInputSpec, CommandLineInputSpec):
    """
    Input specification for the QsireconProcedure
    """

    input_directory = Directory(
        exists=True,
        mandatory=True,
        argstr="-v %s:/data:ro",
        desc="Input directory containing QSIPrep outputs",
    )
    output_directory = Directory(
        exists=False,
        mandatory=True,
        argstr="-v %s:/out",
        desc="Directory to store Qsirecon's output",
    )
    analysis_level = traits.Str(
        mandatory=False,
        desc="Analysis level",
        default_value="participant",
        argstr="%s",
        position=0,
    )
    fs_license_file = File(
        exists=True,
        mandatory=False,
        argstr="-v %s:/fslicense.txt",
        desc="Path to FreeSurfer license file",
    )
    work_directory = Directory(
        exists=False,
        mandatory=True,
        argstr="-v %s:/work",
        desc="Path to work directory",
    )
    qsirecon_version = traits.Str(
        mandatory=False,
        desc="QSIRcon version",
        default_value="latest",
        argstr="%s",
    )
    participant_label = traits.Str(
        argstr="--participant-label %s",
        desc="Participant label",
    )
    recon_spec = File(
        exists=True,
        argstr="-v %s:/recon-spec.yaml",
        desc="Path to recon-spec YAML file",
    )
    force = traits.Bool(
        False,
        usedefault=True,
        desc="Whether to force the procedure to run even if the output directory already exists.",
    )


class QsireconOutputSpec(ProcedureOutputSpec):
    """
    Output specification for the QsireconProcedure
    """

    output_directory = Directory(
        exists=True,
        desc="Directory where Qsirecon outputs are stored",
    )
    log_file = File(
        exists=True,
        desc="Qsirecon log file",
    )


class QsireconProcedure(Procedure, CommandLine):
    """
    Procedure for running Qsiprep
    """

    _cmd_prefix = "docker run --rm"
    _cmd = "pennlinc/qsirecon"
    input_spec = QsireconInputSpec
    output_spec = QsireconOutputSpec
    _version = "0.0.1"

    def __init__(self, **inputs: Any):
        super().__init__(**inputs)

    def _parse_mounted_inputs(self):
        """
        Parse mounted inputs
        """
        return [inp for inp in self._parse_inputs() if inp.startswith("-v")]

    def _parse_cmd_inputs(self):
        """
        Parse command inputs
        """
        all_args = []
        metadata = dict(argstr=lambda t: t is not None)
        for name, spec in sorted(self.inputs.traits(**metadata).items()):
            if name == "qsirecon_version":
                continue
            argstr = spec.argstr
            if "-v " in argstr:
                continue
            value = getattr(self.inputs, name)
            if not isdefined(value):
                continue
            arg = self._format_arg(name, spec, value)
            all_args += [arg]
        return all_args

    def _get_default_value(self, key: str) -> Any:
        """
        Get the default value of an input
        """
        value = getattr(self.inputs, key)
        return value if isdefined(value) else self.inputs.traits().get(key).default

    def _add_mounts_to_command(
        self,
        mounts: dict = {
            "fs_license_file": "--fs-license-file",
            "work_directory": "--work-dir",
            "recon_spec": "--recon-spec",
        },
    ):
        """
        Add mounts to the command
        """
        args = []
        for key, argstr in mounts.items():
            value = getattr(self.inputs, key)
            if isdefined(value):
                mounted_destination = (
                    self.inputs.traits().get(key).argstr.split(":")[-1]
                )
                args += [f"{argstr} {mounted_destination}"]
        return args

    def run_procedure(self, **kwargs):
        """
        Run the QsiprepProcedure

        Raises
        ------
        CalledProcessError
            If the command fails to run. The error message will be logged.
        """
        self._locate_fs_license_file()
        self.setup_logging()
        self.logger.info("Running QsireconProcedure")
        self.logger.debug(f"Input attributes: {kwargs}")

        if not self.inputs.force:
            self.logger.info(
                f"Attempting to locate outputs from previous run in {self.inputs.output_directory}"
            )
            result = self._list_outputs()
            if all(Path(value).exists() for value in result.values()):
                self.logger.info(
                    f"Outputs already exist in {self.inputs.output_directory}. If you want to run the procedure again, set force=True."
                )
                return
        finished_file, proceed = self._check_old_runs_finished()
        if not proceed:
            self.logger.info(
                f"Previous run detected as finished in {self.inputs.output_directory}. If you want to run the procedure again, set force=True."  # noqa: E501
            )
            return
        # Prepare inputs
        temp_input_directory = self._prepare_inputs()
        # Run the qsiprep command
        command = self.cmdline
        # Log the command
        self.logger.info(f"Running command: {command}")
        result = run(
            command,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
        )
        self.logger.info(result.stdout)
        if result.stderr:
            self.logger.error(result.stderr)
            raise CalledProcessError(
                result.returncode, command, output=result.stdout, stderr=result.stderr
            )
        self.logger.info("Finished running SmriprepProcedure")
        self.logger.info(
            f"Cleaning up temporary input directory: {temp_input_directory}"
        )
        # Clean up
        run(f"rm -rf {temp_input_directory}", shell=True, check=True)
        self._write_finished_file(finished_file)

    def _locate_fs_license_file(self):
        """
        Locate the FreeSurfer license file
        """
        if not isdefined(self.inputs.fs_license_file):
            fs_home = os.getenv("FREESURFER_HOME")
            if fs_home is None:
                raise ValueError(
                    "FREESURFER_HOME environment variable is not set and fs_license_file is not provided."
                )
            fs_license_file = Path(fs_home) / "license.txt"
            if not fs_license_file.exists():
                raise ValueError(
                    f"FreeSurfer license file not found at {fs_license_file}"
                )
            self.inputs.fs_license_file = str(Path(fs_home) / "license.txt")

    def _prepare_inputs(self):
        """
        Prepare inputs for the QsireconProcedure
        """
        work_directory = Path(self.inputs.work_directory)
        input_directory = Path(self.inputs.input_directory)
        temp_bids = work_directory / self.log_file_path.stem / "qsiprep"
        temp_bids.mkdir(parents=True, exist_ok=True)
        # rsync input directory to work directory
        run(
            f"rsync -azPL {input_directory}/sub-{self.inputs.participant_label} {temp_bids}",
            shell=True,
            check=True,
        )
        for fname in [
            "dataset_description.json",
            # "participants.tsv",
            # "participants.json",
            # "README",
        ]:
            run(
                f"rsync -azPL {input_directory / fname} {temp_bids}",
                shell=True,
                check=True,
            )
        self.inputs.input_directory = temp_bids
        return temp_bids

    @property
    def cmdline(self):
        """`command` plus any arguments (args)
        validates arguments and generates command line"""
        self._check_mandatory_inputs()
        allargs = (
            [self._cmd_prefix]
            + self._parse_mounted_inputs()
            + [f"{self._cmd}:{self._get_default_value('qsirecon_version')} /data /out"]
            + [self._get_default_value("analysis_level")]
            + self._parse_cmd_inputs()
            + self._add_mounts_to_command()
        )
        return " ".join(allargs)

    def _list_outputs(self) -> Dict[str, str]:
        """
        List the outputs of the QsiprepProcedure
        """
        output_directory = Path(self.inputs.output_directory)
        if output_directory.name != "qsiprep":
            output_directory = output_directory / "qsiprep"
        output_directory = (
            output_directory / f"sub-{self.inputs.participant_label}.html"
        )
        outputs = self._outputs().get()
        outputs["output_directory"] = str(output_directory)
        if hasattr(self, "log_file_path"):
            outputs["log_file"] = str(self.log_file_path)
        return outputs

    @property
    def sessions(self):
        """
        Get the sessions
        """
        return [
            session.name.split("-")[-1]
            for session in Path(self.inputs.input_directory).glob("ses-*")
            if session.is_dir()
        ]

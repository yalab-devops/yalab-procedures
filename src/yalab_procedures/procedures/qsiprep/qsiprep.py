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


class QsiprepInputSpec(ProcedureInputSpec, CommandLineInputSpec):
    """
    Input specification for the QsiprepProcedure
    """

    input_directory = Directory(
        exists=True,
        mandatory=True,
        argstr="-v %s:/data:ro",
        desc="Input directory containing preprocessed data",
    )
    output_directory = Directory(
        exists=False,
        mandatory=True,
        argstr="-v %s:/out",
        desc="Directory to store Qsiprep's output",
    )
    analysis_level = traits.Str(
        mandatory=False,
        desc="Analysis level",
        default_value="participant",
        argstr="%s",
        position=0,
    )
    output_resolution = traits.Float(
        mandatory=True,
        desc="Output resolution in mm",
        argstr="--output-resolution %s",
        default_value=1.6,
        usedefault=True,
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
    qsiprep_version = traits.Str(
        mandatory=False,
        desc="QSIprep version",
        default_value="latest",
        argstr="%s",
    )
    participant_label = traits.List(
        traits.Str,
        argstr="--participant_label %s",
        desc="Participant label",
        sep=",",
    )
    output_spaces = traits.List(
        traits.Str,
        argstr="--anatomical-template %s",
        desc="Output spaces",
        sep=",",
    )
    longitudinal = traits.Bool(
        True,
        argstr="--longitudinal",
        desc="Longitudinal processing. May increase runtime.",
    )
    bids_filters = traits.File(
        exists=True,
        argstr="-v %s:/bids_filters.json",
        desc="BIDS filter file",
    )
    no_b0_harmonization = traits.Bool(
        False,
        argstr="--no-b0-harmonization",
        desc="Disable B0 harmonization",
    )
    skip_bids_validation = traits.Bool(
        False,
        argstr="--skip-bids-validation",
        desc="Skip BIDS validation",
    )
    nprocs = traits.Int(
        os.cpu_count(),
        usedefault=True,
        desc="Number of processes (compute tasks) that can be run in parallel (multiprocessing only).",
    )
    omp_nthreads = traits.Int(
        1,
        usedefault=True,
        desc="Number of CPUs a single process can access for multithreaded execution.",
    )

    force = traits.Bool(
        False,
        usedefault=True,
        desc="Whether to force the procedure to run even if the output directory already exists.",
    )


class QsiprepOutputSpec(ProcedureOutputSpec):
    """
    Output specification for the QsiprepProcedure
    """

    output_directory = Directory(
        exists=True,
        desc="Directory where Qsiprep outputs are stored",
    )
    log_file = File(
        exists=True,
        desc="Qsiprep log file",
    )


class QsiprepProcedure(Procedure, CommandLine):
    """
    Procedure for running Qsiprep
    """

    _cmd_prefix = "docker run --rm"
    _cmd = "pennlinc/qsiprep"
    input_spec = QsiprepInputSpec
    output_spec = QsiprepOutputSpec
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
            if name == "qsiprep_version":
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
            "bids_filters": "--bids-filter-file",
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
        self.logger.info("Running QsiprepProcedure")
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
        Prepare inputs for the QsiprepProcedure
        """
        work_directory = Path(self.inputs.work_directory)
        input_directory = Path(self.inputs.input_directory)
        temp_bids = work_directory / self.log_file_path.stem / "bids"
        temp_bids.mkdir(parents=True, exist_ok=True)
        # rsync input directory to work directory
        for participant in self.inputs.participant_label:
            run(
                f"rsync -azPL {input_directory}/sub-{participant} {temp_bids}",
                shell=True,
                check=True,
            )
        for fname in [
            "dataset_description.json",
            "participants.tsv",
            "participants.json",
            "README",
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
            + [f"{self._cmd}:{self._get_default_value('qsiprep_version')} /data /out"]
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

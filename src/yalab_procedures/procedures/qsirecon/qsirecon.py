import os
import shlex
import shutil
from glob import glob
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
    temporary_bids_directory = Directory(
        exists=False,
        mandatory=False,
        desc="Temporary QSIPrep directory",
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
    fs_subjects_dir = Directory(
        exists=False,
        mandatory=False,
        argstr="-v %s:/fs_subjects_dir",
        desc="Path to FreeSurfer subjects directory",
    )
    run_recon_all = traits.Bool(
        False,
        usedefault=True,
        desc="If True, run FreeSurfer recon-all on QSIPrep's subject-level T1 before qsirecon.",
    )
    use_flair = traits.Bool(
        False,
        usedefault=True,
        desc="If True, include QSIPrep's preprocessed FLAIR with -FLAIR -FLAIRpial in recon-all if available.",
    )
    freesurfer_image = traits.Str(
        "freesurfer/freesurfer:7.4.1",
        usedefault=True,
        desc="Docker image tag for FreeSurfer.",
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
    atlases = traits.List(
        traits.Str(),
        argstr="--atlases %s",
        sep=" ",
        desc="List of atlases to use",
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
            "fs_subjects_dir": "--fs-subjects-dir",
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

        # OPTIONAL: run recon-all first
        if self.inputs.run_recon_all:
            fsdir = self._ensure_fs_subjects_dir()
            t1, flair = self._locate_qsiprep_preproc_anat()
            self._run_recon_all(fsdir, t1, flair)
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
        temporary_bids_directory = self.inputs.temporary_bids_directory
        if isdefined(temporary_bids_directory):
            temp_bids = Path(temporary_bids_directory)
            temp_bids.mkdir(parents=True, exist_ok=True)
        else:
            temp_bids = work_directory
        # generate random temporary directory
        temp_bids = temp_bids / f"qsirecon_temp_bids_{os.getpid()}"
        self.logger.info(f"Using provided temporary BIDS directory: {temp_bids}")
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
        if output_directory.name != "qsirecon":
            output_directory = output_directory / "qsirecon"
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

    def _ensure_fs_subjects_dir(self) -> Path:
        """
        Ensure a writable FreeSurfer subjects dir exists and is mounted later.
        If the user didn't provide one, create under work/<logstem>/freesurfer.
        """
        if isdefined(self.inputs.fs_subjects_dir):
            fsdir = Path(self.inputs.fs_subjects_dir)
        else:
            input_dir = Path(self.inputs.input_directory)
            if input_dir.name == "qsiprep":
                input_dir = input_dir.parent
            fsdir = Path(input_dir) / "freesurfer"
            fsdir.mkdir(parents=True, exist_ok=True)
            # wire it into inputs so the existing -v %s:/fs_subjects_dir mount is added
            self.inputs.fs_subjects_dir = str(fsdir)
        fsdir.mkdir(parents=True, exist_ok=True)
        return fsdir

    def _locate_qsiprep_preproc_anat(self) -> tuple[str, str | None]:
        """
        Locate QSIPrep's subject-level preprocessed T1 (and optional FLAIR) inside the
        temp input directory we created (_prepare_inputs). Prefer the subject-level anat
        (sub-<id>/anat/sub-<id>_desc-preproc_T1w.nii.gz). Fallback to first session.
        """
        sub = f"sub-{self.inputs.participant_label}"
        root = Path(self.inputs.input_directory)

        # Subject-level preferred
        t1_candidates = sorted(
            glob(str(root / sub / "anat" / f"{sub}_space-ACPC_desc-preproc_T1w.nii.gz"))
        )
        flair_candidates = sorted(
            glob(
                str(root / sub / "anat" / f"{sub}_space-ACPC_desc-preproc_FLAIR.nii.gz")
            )
        )

        # Fallback to any session if subject-level not present
        if not t1_candidates:
            t1_candidates = sorted(
                glob(
                    str(
                        root
                        / sub
                        / "ses-*"
                        / "anat"
                        / f"{sub}_ses-*_desc-preproc_T1w.nii.gz"
                    )
                )
            )
        if not flair_candidates:
            flair_candidates = sorted(
                glob(
                    str(
                        root
                        / sub
                        / "ses-*"
                        / "anat"
                        / f"{sub}_ses-*_desc-preproc_FLAIR.nii.gz"
                    )
                )
            )

        if not t1_candidates:
            raise FileNotFoundError(
                f"Could not find QSIPrep preprocessed T1 for {sub} under {root}. "
                "Expected .../sub-<id>/anat/*desc-preproc_T1w.nii.gz or ses-*/anat/..."
            )

        t1 = t1_candidates[0]
        flair = (
            flair_candidates[0]
            if (self.inputs.use_flair and flair_candidates)
            else None
        )
        return t1, flair

    def locate_fs_run(self, fsdir, sub_id: str) -> Path | None:
        """
        Locate a previous FreeSurfer recon-all run for the given subject ID in the
        provided FreeSurfer subjects directory.
        """
        subject_dir = fsdir / f"sub-{sub_id}"
        if subject_dir.exists():
            if (subject_dir / "scripts" / "recon-all.done").exists():
                return True
            else:
                shutil.rmtree(subject_dir)
        return False

    def _run_recon_all(self, fsdir: Path, t1_path: str, flair_path: str | None):
        """
        Run FreeSurfer recon-all in Docker on the provided T1 (and optional FLAIR).
        Writes to fsdir/sub-<label>. Runs container as host UID:GID to avoid root ownership.
        """
        sub_id = f"sub-{self.inputs.participant_label}"
        if self.locate_fs_run(fsdir, sub_id):
            self.logger.info(
                f"Found existing recon-all output for {sub_id} in {fsdir}, skipping recon-all."
            )
            return
        fs_license = self.inputs.fs_license_file
        if not isdefined(fs_license):
            raise ValueError(
                "fs_license_file must be provided (or FREESURFER_HOME set)."
            )

        # Build docker run
        fsimg = self.inputs.freesurfer_image

        # Mounts
        mounts = [
            f"-v {shlex.quote(t1_path)}:/in/T1.nii.gz:ro",
            f"-v {shlex.quote(str(fsdir))}:/out",
            f"-v {shlex.quote(fs_license)}:/fslicense.txt:ro",
        ]
        flair_mount = (
            f"-v {shlex.quote(flair_path)}:/in/FLAIR.nii.gz:ro" if flair_path else ""
        )
        if flair_mount:
            mounts.append(flair_mount)

        flair_args = "-FLAIR /in/FLAIR.nii.gz -FLAIRpial" if flair_path else ""

        cmd = (
            f"docker run --rm -i {' '.join(mounts)} "
            f"{fsimg} bash -lc "
            f'"export FS_LICENSE=/fslicense.txt; '
            f'recon-all -sd /out -subject {sub_id} -i /in/T1.nii.gz {flair_args} -all"'
        )

        self.logger.info(f"Running recon-all: {cmd}")
        res = run(cmd, shell=True, capture_output=True, text=True)
        self.logger.info(res.stdout)
        if res.returncode != 0:
            self.logger.error(res.stderr)
            raise CalledProcessError(
                res.returncode, cmd, output=res.stdout, stderr=res.stderr
            )

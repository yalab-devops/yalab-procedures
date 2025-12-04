import logging
import os
from pathlib import Path
from subprocess import CalledProcessError, run
from typing import Any, Dict

from nipype.interfaces.base import (
    CommandLineInputSpec,
    Directory,
    File,
    isdefined,
    traits,
)
from parcellate.interfaces.qsirecon.qsirecon import QSIReconConfig, run_parcellations

from yalab_procedures.procedures.base.procedure import (
    Procedure,
    ProcedureInputSpec,
    ProcedureOutputSpec,
)


class QsiparcInputSpec(ProcedureInputSpec, CommandLineInputSpec):
    """
    Input specification for the QsiparcProcedure
    """

    input_directory = Directory(
        exists=True,
        mandatory=True,
        desc="Input directory containing QSIRecon BIDS dataset",
    )
    temporary_bids_directory = Directory(
        exists=False,
        mandatory=False,
        desc="Temporary BIDS directory",
    )
    output_directory = Directory(
        exists=False,
        mandatory=True,
        desc="Directory to store Qsiparc's output",
    )
    work_directory = Directory(
        exists=False,
        mandatory=True,
        desc="Path to work directory",
    )
    participant_label = traits.List(
        traits.Str,
        desc="Participant label",
        sep=",",
    )
    resampling_target = traits.Enum(
        "data",
        "atlas",
        "labels",
        desc="Resampling target for parcellation",
    )
    mask = traits.Str(
        "gm",
        usedefault=True,
        desc="Type of mask to use for parcellation (e.g., 'gm' for gray matter)",
    )
    skip_bids_validation = traits.Bool(
        True,
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


class QsiparcOutputSpec(ProcedureOutputSpec):
    """
    Output specification for the QsiparcProcedure
    """

    output_directory = traits.List(
        Directory,
        desc="Qsiparc output directory",
    )
    log_file = File(
        exists=True,
        desc="Qsiparc log file",
    )


class QsiparcProcedure(Procedure):
    """
    Procedure for running Qsiparc
    """

    input_spec = QsiparcInputSpec
    output_spec = QsiparcOutputSpec
    _version = "0.0.1"

    def __init__(self, **inputs: Any):
        super().__init__(**inputs)

    def _get_default_value(self, key: str) -> Any:
        """
        Get the default value of an input
        """
        value = getattr(self.inputs, key)
        return value if isdefined(value) else self.inputs.traits().get(key).default

    def run_procedure(self, **kwargs):
        """
        Run the QsiparcProcedure
        Raises
        ------
        CalledProcessError
            If the command fails to run. The error message will be logged.
        """
        self.setup_logging()
        self.logger.info("Running QsiparcProcedure")
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
        config = self._initiate_config()
        try:
            _ = run_parcellations(config)
        except Exception as e:
            self.logger.error(f"QsiparcProcedure failed with error: {e}")
            raise CalledProcessError(
                returncode=1,
                cmd="run_parcellations",
                output=str(e),
            ) from e
        self.logger.info("Finished running QSIPrepProcedure")
        self.logger.info(
            f"Cleaning up temporary input directory: {temp_input_directory}"
        )
        # Clean up
        result = run(
            f"rm -rf {temp_input_directory}",
            shell=True,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            self.logger.warning(
                f"Failed to remove temporary input directory: {temp_input_directory}. Error: {result.stderr}"  # noqa: E501
            )
        self._write_finished_file(finished_file)

    def _prepare_inputs(self):
        """
        Prepare inputs for the QsiprepProcedure
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
        temp_bids = temp_bids / f"qsiparc_temp_bids_{os.getpid()}"
        self.logger.info(f"Using provided temporary BIDS directory: {temp_bids}")
        temp_bids.mkdir(parents=True, exist_ok=True)
        # rsync input directory to work directory
        for participant in self.inputs.participant_label:
            run(
                f"rsync -azPL {input_directory}/sub-{participant} {temp_bids}",
                shell=True,
                check=True,
            )
            for derivatives in (input_directory / "derivatives").glob(
                f"qsirecon-*/sub-{participant}"
            ):
                dest = temp_bids / "derivatives" / derivatives.parent.name
                dest.mkdir(parents=True, exist_ok=True)
                run(
                    f"rsync -azPL --exclude='*.tck*' --exclude='*.trk*' {derivatives} {dest}",
                    shell=True,
                    check=True,
                )
                run(
                    f"rsync -azPL {derivatives.parent}/dataset_description.json {temp_bids / 'derivatives'}",
                    shell=True,
                    check=True,
                )
        for fname in ["dataset_description.json", "atlases"]:
            run(
                f"rsync -azPL {input_directory / fname} {temp_bids}",
                shell=True,
                check=True,
            )
        self.inputs.input_directory = temp_bids
        return temp_bids

    def _list_outputs(self) -> Dict[str, str]:
        """
        List the outputs of the QsiparcProcedure
        """
        output_directory = Path(self.inputs.output_directory)
        if output_directory.name != "qsiparc":
            output_directory = output_directory / "qsiparc"
        outputs = self._outputs().get()
        outputs["output_directory"] = [
            d
            for d in Path(output_directory).glob(
                f"*/sub-{self.inputs.participant_label[0]}"
            )
            if d.is_dir()
        ]
        if hasattr(self, "log_file_path"):
            outputs["log_file"] = str(self.log_file_path)
        return outputs

    def _initiate_config(self) -> QSIReconConfig:
        """
        Initialize QSIReconConfig from inputs
        """
        config = QSIReconConfig(
            input_root=Path(self.inputs.input_directory),
            output_dir=Path(self.inputs.output_directory),
            subjects=self.inputs.participant_label,
            resampling_target=self.inputs.resampling_target,
            force=self.inputs.force,
            log_level=logging.DEBUG,
            mask=self.inputs.mask,
        )
        return config

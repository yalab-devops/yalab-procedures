import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Union

from nipype.interfaces.base import (
    BaseInterface,
    BaseInterfaceInputSpec,
    Directory,
    TraitedSpec,
    isdefined,
    traits,
)


class ProcedureInputSpec(BaseInterfaceInputSpec):
    input_directory = Directory(
        exists=True, mandatory=True, desc="Input directory"
    )  # noqa: E501
    output_directory = Directory(mandatory=True, desc="Output directory")
    logging_directory = Directory(desc="Logging directory")
    logging_level = traits.Enum(
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
        desc="Logging level",
        usedefault=True,
        default="INFO",
    )
    force = traits.Bool(
        False,
        usedefault=True,
        desc="Whether to force the procedure to run even if the output directory already exists.",  # noqa: E501
    )


class ProcedureOutputSpec(TraitedSpec):
    output_directory = Directory(desc="Output directory")
    log_file = traits.File(desc="Log file")


class Procedure(BaseInterface):
    input_spec = ProcedureInputSpec
    output_spec = ProcedureOutputSpec
    _version = "0.0.1"

    def __init__(self, **inputs: Any):
        super().__init__(**inputs)

    def _run_interface(self, runtime) -> Any:
        """
        Executes the interface, setting up logging and calling the procedure.
        """
        # Validate directories and set up logging
        if not isdefined(self.inputs.logging_directory):
            self.inputs.logging_directory = (
                Path(self.inputs.output_directory).parent / "logs"
            )

        self.setup_logging()

        # Check if the procedure has already been run
        finished_file, proceed = self._check_old_runs_finished()
        if not proceed:
            return runtime

        self.logger.info(
            f"Running procedure with input directory: {self.inputs.input_directory}"  # noqa: E501
        )
        # Run the custom procedure
        self.run_procedure(**self.inputs.get())
        self.logger.info(
            f"Procedure completed. Output directory: {self.inputs.output_directory}"  # noqa: E501
        )
        self._write_finished_file(finished_file)

        return runtime

    def _check_old_runs_finished(self) -> Any:
        """
        Logs the completion of the procedure.
        """
        # set up a "finished" file to keep track of when the procedure was last run # noqa: E501
        finished_file = (
            Path(self.inputs.logging_directory)
            / f"{type(self).__name__}-{self._version}.done.json"
        )
        proceed = True
        if finished_file.exists():
            if self.inputs.force:
                self.logger.info(
                    f"Removing {finished_file} because force=True. Will run procedure again."  # noqa: E501
                )
                finished_file.unlink()
                return finished_file, proceed
            # read the timestamp of the last run from the file
            with open(str(finished_file), "r") as f:
                data = json.load(f)
                timestamp = data["timestamp"]
                config = data["config"]
            self.logger.info(
                f"Procedure was last run on {timestamp}. Checking if the configuration is the same."  # noqa: E501
            )
            # check if the configuration is the same as the current configuration # noqa: E501
            if self.inputs.output_directory == config["output_directory"]:
                msg = "User requested to regenerate outputs in the same directory. Please change the output directory or set force=True."  # noqa: E501
                self.logger.error(
                    msg,
                )
                proceed = False
            else:
                proceed = True
        return finished_file, proceed

    def _write_finished_file(self, finished_file: Union[str, Path]):
        """
        Writes a "finished" file to keep track of when the procedure was last run. # noqa: E501

        Parameters
        ----------
        finished_file : Union[str, Path]
            The path to the finished file.
        """
        config_to_save = {}
        # Fix JSON serialization issues
        for key, value in self.inputs.get().items():
            if isinstance(value, Path):
                config_to_save[key] = str(value)
            elif not isdefined(value):
                config_to_save[key] = None  # type: ignore[assignment]
            else:
                config_to_save[key] = value
        with open(str(finished_file), "w") as f:
            json.dump(
                {"timestamp": str(datetime.now()), "config": config_to_save},
                f,  # noqa: E501
                indent=6,
            )

    def _check_same_configuration(self, config: Dict[str, Any]) -> bool:
        """
        Checks if the configuration of the procedure is the same as the provided configuration. # noqa: E501
        """
        # checks whether the provided configuration is the same as the current configuration # noqa: E501
        current_config = self.inputs.get()
        return current_config == config

    def _list_outputs(self) -> Dict[str, str]:
        """
        Lists the outputs of the procedure.
        """
        outputs = self._outputs().get()
        outputs["output_directory"] = str(self.inputs.output_directory)
        outputs["log_file"] = str(self.log_file_path)
        return outputs

    def _gen_log_filename(self) -> str:
        """
        Generates a log filename based on the procedure name and the current timestamp.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{self.__class__.__name__}_{timestamp}.log"

    def setup_logging(self):
        """
        Sets up logging configuration.
        """
        # Reset logging configuration
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        # Set up logging configuration
        logging_dir = Path(self.inputs.logging_directory)
        if not logging_dir.exists():
            logging_dir.mkdir(parents=True, exist_ok=True)

        log_file_path = logging_dir / self._gen_log_filename()
        self.log_file_path = log_file_path
        logging.basicConfig(
            filename=log_file_path,
            level=getattr(logging, self.inputs.logging_level),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(self.__class__.__name__)

        self.logger.debug(f"Logging setup complete. Log file: {log_file_path}")

    def run_procedure(self, **kwargs):
        """
        This method should be implemented by subclasses to define the specific steps of the procedure.
        """
        raise NotImplementedError("Subclasses should implement this method")

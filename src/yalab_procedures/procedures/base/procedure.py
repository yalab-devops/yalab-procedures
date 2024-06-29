import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from nipype.interfaces.base import (
    BaseInterface,
    BaseInterfaceInputSpec,
    Directory,
    TraitedSpec,
    isdefined,
    traits,
)


class ProcedureInputSpec(BaseInterfaceInputSpec):
    input_directory = Directory(exists=True, mandatory=True, desc="Input directory")
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


class ProcedureOutputSpec(TraitedSpec):
    output_directory = Directory(desc="Output directory")
    log_file = traits.File(desc="Log file")


class Procedure(BaseInterface):
    input_spec = ProcedureInputSpec
    output_spec = ProcedureOutputSpec

    def _run_interface(self, runtime) -> Any:
        """
        Executes the interface, setting up logging and calling the procedure.
        """
        # Extract input attributes as a dictionary
        input_attributes = self._get_inputs_as_kwargs()

        # Validate directories and set up logging
        input_attributes["input_directory"] = Path(input_attributes["input_directory"])
        input_attributes["output_directory"] = Path(
            input_attributes["output_directory"]
        )
        if "logging_directory" in input_attributes:
            input_attributes["logging_directory"] = Path(
                input_attributes["logging_directory"]
            )
        else:
            input_attributes["logging_directory"] = input_attributes["output_directory"]

        self.setup_logging(
            input_attributes["logging_directory"], input_attributes["logging_level"]
        )

        self.logger.info(
            f"Running procedure with input directory: {input_attributes['input_directory']}"
        )

        # Run the custom procedure
        self.run_procedure(**input_attributes)

        return runtime

    def _list_outputs(self) -> Dict[str, str]:
        """
        Lists the outputs of the procedure.
        """
        outputs = self._outputs().get()
        outputs["output_directory"] = str(self.inputs.output_directory)
        outputs["log_file"] = self.log_file_path
        return outputs

    def _gen_log_filename(self) -> str:
        """
        Generates a log filename based on the procedure name and the current timestamp.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{self.__class__.__name__}_{timestamp}.log"

    def setup_logging(self, logging_dir: Path, logging_level: str):
        """
        Sets up logging configuration.
        """
        # Reset logging configuration
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        if not logging_dir.exists():
            logging_dir.mkdir(parents=True, exist_ok=True)

        log_file_path = logging_dir / self._gen_log_filename()
        self.log_file_path = log_file_path
        logging.basicConfig(
            filename=log_file_path,
            level=getattr(logging, logging_level),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(self.__class__.__name__)

        self.logger.debug(f"Logging setup complete. Log file: {log_file_path}")

    def run_procedure(self, **kwargs):
        """
        This method should be implemented by subclasses to define the specific steps of the procedure.
        """
        raise NotImplementedError("Subclasses should implement this method")

    def _get_inputs_as_kwargs(self) -> Dict[str, Any]:
        """
        Extracts defined inputs from the input spec as a dictionary of keyword arguments.
        """
        input_values = {
            name: getattr(self.inputs, name)
            for name in self.inputs.__dict__.keys()
            if isdefined(getattr(self.inputs, name))
        }
        return input_values

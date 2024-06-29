# src/yalab_procedures/procedures/procedure.py

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
    input_directory = Directory(exists=True, mandatory=True, desc="Input directory")
    output_directory = Directory(mandatory=True, desc="Output directory")
    config = traits.Either(
        traits.Dict(traits.Str, traits.Any),
        traits.File(exists=True),
        mandatory=True,
        desc="Configuration settings as a dictionary or a path to a JSON file",
        usedefault=True,
        default={},
    )
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


class Procedure(BaseInterface):
    input_spec = ProcedureInputSpec
    output_spec = ProcedureOutputSpec
    config_keys = [
        "input_directory",
        "output_directory",
        "logging_directory",
        "logging_level",
    ]

    def _run_interface(self, runtime) -> Any:
        """
        Executes the interface, setting up logging and calling the procedure.
        """
        config = self.load_config(self.inputs.config)
        self.validate_and_set_inputs(config)

        input_dir = Path(self.inputs.input_directory)
        output_dir = Path(self.inputs.output_directory)
        logging_dir = (
            Path(self.inputs.logging_directory)
            if isdefined(self.inputs.logging_directory)
            else output_dir
        )
        logging_level = (
            self.inputs.logging_level
            if isdefined(self.inputs.logging_level)
            else "INFO"
        )

        # Set up logging
        self.setup_logging(logging_dir, logging_level)

        self.logger.info(f"Running procedure with input directory: {input_dir}")

        # Run the custom procedure
        self.run_procedure(input_dir, output_dir, config, logging_dir)

        return runtime

    def _list_outputs(self) -> Dict[str, str]:
        """
        Lists the outputs of the procedure.
        """
        outputs = self._outputs().get()
        outputs["output_directory"] = str(self.inputs.output_directory)
        return outputs

    def setup_logging(self, logging_dir: Path, logging_level: str):
        """
        Sets up logging configuration.
        """
        # Reset logging configuration
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        if not logging_dir.exists():
            logging_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"{self.__class__.__name__}_{timestamp}.log"
        log_file_path = logging_dir / log_filename

        logging.basicConfig(
            filename=log_file_path,
            level=getattr(logging, logging_level),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(self.__class__.__name__)

        self.logger.debug(f"Logging setup complete. Log file: {log_file_path}")

    def load_config(self, config: Union[Dict[str, Any], str]) -> Dict[str, Any]:
        """
        Loads the configuration from a dictionary or a JSON file.
        """
        if isinstance(config, dict):
            return config
        elif isinstance(config, str):
            with open(config, "r") as f:
                return json.load(f)
        else:
            raise ValueError(
                "Config must be either a dictionary or a path to a JSON file."
            )

    def validate_and_set_inputs(self, config: Dict[str, Any]):
        """
        Validates the keys in the config and sets the inputs.
        """
        for key, value in config.items():
            if key in self.config_keys:
                setattr(self.inputs, key, value)
            else:
                raise ValueError(f"Invalid config key: {key}")

    def run_procedure(
        self,
        input_dir: Path,
        output_dir: Path,
        config: Dict[str, Any],
        logging_dest: Path,
    ):
        """
        This method should be implemented by subclasses to define the specific steps of the procedure.
        """
        raise NotImplementedError("Subclasses should implement this method")

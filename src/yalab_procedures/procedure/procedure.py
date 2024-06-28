import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional, Union


class Procedure(ABC):
    """
    Abstract base class for procedures.

    Parameters
    ----------
    input_directory : Union[str, Path]
        The path to the input directory.
    output_directory : Union[str, Path]
        The path to the outputs directory.
    config : Optional[Union[dict[str, str], str, Path]]
        The configuration settings for the procedure.
    logging_destination : Optional[Union[str, Path]]
        The path to the logging directory.
    logging_level : str
        The logging level.
    """

    def __init__(
        self,
        input_directory: Union[str, Path],
        output_directory: Union[str, Path],
        config: Optional[Union[dict[str, str], str, Path]] = None,
        logging_destination: Optional[Union[str, Path]] = None,
        logging_level: str = "INFO",
    ):
        self.logging_destination = (
            Path(logging_destination) if logging_destination else Path(output_directory)
        )
        self.logging_level = logging_level
        self.logger = logging.getLogger(self.__class__.__name__)
        self._setup_logging()
        self.input_directory = self._validate_input_directory(input_directory)
        self.config = self._load_config(config)
        self.output_directory = self._setup_output_directory(output_directory)

    @abstractmethod
    def run(self) -> None:
        """
        Abstract method to run the procedure.
        """
        raise NotImplementedError(
            "This is the abstract method for the Procedure class. It should be implemented in the child class."
        )

    def _validate_input_directory(self, input_directory: Union[Path, str]) -> Path:
        """
        Validates the input directory.

        Parameters
        ----------
        input_directory : Union[Path, str]
            The input directory to validate.

        Raises
        ------
        FileNotFoundError
            If the input directory does not exists.

        Returns
        -------
        Path
            The input directory as a Path object.
        """
        input_directory = Path(input_directory)
        if input_directory.is_dir():
            return input_directory
        else:
            raise FileNotFoundError(f"Input directory {input_directory} not found.")

    def _setup_output_directory(self, output_directory: Union[str, Path]) -> Path:
        """
        Sets up the output directory.

        Parameters
        ----------
        output_directory : Union[str, Path]
            The output directory to set up.

        Returns
        -------
        Path
            The output directory as a Path object.
        """
        output_directory = Path(output_directory)
        if output_directory.is_dir():
            self.log(f"Output directory {output_directory} already exists.")
        else:
            output_directory.mkdir(parents=True, exist_ok=True)
            self.log(f"Output directory {output_directory} created.")
        return output_directory

    def _setup_logging(self) -> None:
        """
        Sets up the logging for the procedure.
        """
        handler: logging.Handler
        if self.logging_destination:
            self.logging_destination.mkdir(
                parents=True, exist_ok=True
            )  # Ensure the logging directory exists
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"{self.__class__.__name__}_{timestamp}.log"
            log_file_path = self.logging_destination / log_filename
            handler = logging.FileHandler(log_file_path)
        else:
            handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(getattr(logging, self.logging_level.upper(), "INFO"))

    def log(self, message: str) -> None:
        """
        Logs a message at the INFO level.

        Parameters
        ----------
        message : str
            The message to log.
        """
        self.logger.info(message)

    def _load_config(
        self, config: Union[dict[str, str], str, Path, None]
    ) -> dict[str, str]:
        """
        Loads the configuration from a file or dictionary.

        Parameters
        ----------
        config : Union[dict, str, Path, None]
            Configuration settings or path to the configuration file.

        Returns
        -------
        dict
            The configuration dictionary.
        """
        if isinstance(config, dict):
            return config
        elif isinstance(config, (str, Path)):
            config_path = Path(config)
            if config_path.is_file():
                try:
                    with open(config_path, "r") as file:
                        return dict(json.load(file))
                except json.JSONDecodeError:
                    self.log(f"Error decoding JSON from {config_path}")
                    return {}
        return {}

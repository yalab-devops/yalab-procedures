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
    inputs : Union[str, Path]
        Path to the input data.
    config : Union[dict, str, Path], optional
        Configuration settings or path to the configuration file, by default None.
    outputs_destination : Union[str, Path], optional
        Path to the output data, by default None.
    logging_destination : Union[str, Path], optional
        Path to the log file, by default None.
    logging_level : str, optional
        Logging level, by default "INFO".
    """

    def __init__(
        self,
        inputs: Union[str, Path],
        outputs_destination: Union[str, Path],
        config: Optional[Union[dict[str, str], str, Path]] = None,
        logging_destination: Optional[Union[str, Path]] = None,
        logging_level: str = "INFO",
    ):
        self.inputs = Path(inputs)
        self.config = self._load_config(config)
        self.outputs_destination = Path(outputs_destination)
        self.logging_destination = (
            Path(logging_destination)
            if logging_destination
            else self.outputs_destination
        )
        self.logging_level = logging_level
        self.logger = logging.getLogger(self.__class__.__name__)
        self._setup_logging()

    @abstractmethod
    def run(self) -> None:
        """
        Abstract method to run the procedure.
        """
        raise NotImplementedError(
            "This is the abstract method for the Procedure class. It should be implemented in the child class."
        )

    def _setup_logging(self) -> None:
        """
        Sets up logging configuration.
        """
        handler: logging.Handler
        if self.logging_destination:
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
        Optional[dict]
            The configuration dictionary.
        """
        if isinstance(config, dict):
            return config
        elif isinstance(config, (str, Path)):
            config_path = Path(config)
            if config_path.is_file():
                with open(config_path, "r") as file:
                    return dict(json.load(file))
        return {}

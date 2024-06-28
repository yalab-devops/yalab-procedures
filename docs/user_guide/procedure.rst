Procedure Class
===============

The `Procedure` class is an abstract base class designed to standardize and streamline the preprocessing of MRI data. Researchers can extend this class to create custom procedures by implementing the `run` method.

Overview
--------

The `Procedure` class provides a common interface and utilities for data preprocessing tasks. It ensures that all derived procedures follow a consistent pattern for logging, configuration management, and directory validation.

Key Features
------------

- **Abstract Base Class**: The `Procedure` class is designed to be inherited by specific procedure implementations.
- **Configuration Management**: Supports loading configurations from dictionaries or JSON files.
- **Logging**: Standardized logging setup that creates log files in the specified directory.
- **Directory Validation**: Ensures that input and output directories exist and are correctly set up.

Constructor
-----------

The constructor initializes the procedure with specified directories, configuration, and logging settings.

.. code-block:: python

    def __init__(
        self,
        input_directory: Union[str, Path],
        output_directory: Union[str, Path],
        config: Optional[Union[dict[str, str], str, Path]] = None,
        logging_destination: Optional[Union[str, Path]] = None,
        logging_level: str = "INFO",
    )

Parameters:

- **input_directory** (Union[str, Path]): The path to the input directory.
- **output_directory** (Union[str, Path]): The path to the output directory.
- **config** (Optional[Union[dict[str, str], str, Path]]): The configuration settings for the procedure.
- **logging_destination** (Optional[Union[str, Path]]): The path to the logging directory.
- **logging_level** (str): The logging level.

Methods
-------

run()
^^^^^^

The `run` method is an abstract method that must be implemented by any class that inherits from `Procedure`. It contains the logic for the specific procedure.

.. code-block:: python

    @abstractmethod
    def run(self) -> None:
        raise NotImplementedError(
            "This is the abstract method for the Procedure class. It should be implemented in the child class."
        )

_validate_input_directory()
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Validates the input directory to ensure it exists.

.. code-block:: python

    def _validate_input_directory(self, input_directory: Union[Path, str]) -> Path:
        input_directory = Path(input_directory)
        if input_directory is_dir():
            return input_directory
        else:
            raise FileNotFoundError(f"Input directory {input_directory} not found.")

_setup_output_directory()
^^^^^^^^^^^^^^^^^^^^^^^^^^

Sets up the output directory, creating it if it does not exist.

.. code-block:: python

    def _setup_output_directory(self, output_directory: Union[str, Path]) -> Path:
        output_directory = Path(output_directory)
        if output_directory is_dir():
            self.log(f"Output directory {output_directory} already exists.")
        else:
            output_directory.mkdir(parents=True, exist_ok=True)
            self.log(f"Output directory {output_directory} created.")
        return output_directory

_setup_logging()
^^^^^^^^^^^^^^^^^^

Sets up the logging configuration, creating a log file in the specified directory.

.. code-block:: python

    def _setup_logging(self) -> None:
        handler: logging.Handler
        if self.logging_destination:
            self.logging_destination.mkdir(parents=True, exist_ok=True)
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
        self._handler = handler

log()
^^^^^^

Logs a message at the INFO level.

.. code-block:: python

    def log(self, message: str) -> None:
        self.logger.info(message)

_load_config()
^^^^^^^^^^^^^^^^

Loads the configuration from a dictionary or a JSON file.

.. code-block:: python

    def _load_config(
        self, config: Union[dict[str, str], str, Path, None]
    ) -> dict[str, str]:
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


Creating a Custom Procedure
----------------------------

To create a custom procedure, extend the `Procedure` class and implement the `run` method with your specific logic.


Example
^^^^^^^^

.. code-block:: python

    from src.yalab_procedures.procedures.procedure import Procedure

    class CustomProcedure(Procedure):
        def run(self):
            self.log("Running the custom procedure")
            # Custom procedure implementation here

    custom_procedure = CustomProcedure(
        input_directory="path/to/input",
        output_directory="path/to/output",
        config={"param1": "value1"},
        logging_destination="path/to/logs",
        logging_level="DEBUG"
    )
    custom_procedure.run()

Using the Procedure Class
-------------------------

1. **Initialize the Procedure**: Provide the required directories and configuration.
2. **Implement the `run` Method**: Define the specific steps of your procedure.
3. **Run the Procedure**: Call the `run` method to execute the procedure.

Example
^^^^^^^^

.. code-block:: python

    procedure = CustomProcedure(
        input_directory="path/to/input",
        output_directory="path/to/output",
        config="path/to/config.json",
        logging_destination="path/to/logs",
        logging_level="INFO"
    )
    procedure.run()

Logging
^^^^^^^^

Logs are saved in the specified logging directory with a timestamped filename. The logging level can be adjusted to control the verbosity of the log output.

Configuration
^^^^^^^^^^^^^^

Configuration settings can be passed as a dictionary or loaded from a JSON file. This flexibility allows for easy adjustments and reuse of settings across different procedures.

Conclusion
^^^^^^^^^^^

The `Procedure` class provides a robust framework for standardizing data preprocessing tasks in your lab. By extending this class, you can create custom procedures that follow a consistent pattern, making it easier to manage and maintain your data processing workflows.

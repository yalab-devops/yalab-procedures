Procedure Class
===============

The `Procedure` class is an abstract base class designed to standardize and streamline the preprocessing of MRI data. Researchers can extend this class to create custom procedures by implementing the `run_procedure` method.

Overview
--------

The `Procedure` class provides a common interface and utilities for data preprocessing tasks. It ensures that all derived procedures follow a consistent pattern for logging, configuration management, and directory validation.

Key Features
------------

- **Abstract Base Class**: Designed to be inherited by specific procedure implementations.
- **Logging**: Standardized logging setup that creates log files in the specified directory.
- **Directory Validation**: Ensures that input and output directories exist and are correctly set up.

Constructor
-----------

The constructor initializes the procedure with specified directories and logging settings.

.. code-block:: python

    def __init__(
        self,
        input_directory: Union[str, Path],
        output_directory: Union[str, Path],
        logging_directory: Optional[Union[str, Path]] = None,
        logging_level: str = "INFO",
    )

Parameters:

- **input_directory** (`Union[str, Path]`): The path to the input directory.
- **output_directory** (`Union[str, Path]`): The path to the output directory.
- **logging_directory** (`Optional[Union[str, Path]]`): The path to the logging directory.
- **logging_level** (`str`): The logging level.

Methods
-------

_run_interface()
^^^^^^^^^^^^^^^^

The `_run_interface` method sets up logging and calls the `run_procedure` method. This method should not be overridden.

.. code-block:: python

    def _run_interface(self, runtime) -> Any:
        # Sets up logging and calls the custom procedure

_list_outputs()
^^^^^^^^^^^^^^^^

The `_list_outputs` method lists the outputs of the procedure.

.. code-block:: python

    def _list_outputs(self) -> Dict[str, str]:
        # Lists the outputs of the procedure

setup_logging()
^^^^^^^^^^^^^^^^

The `setup_logging` method sets up the logging configuration, creating a log file in the specified directory.

.. code-block:: python

    def setup_logging(self, logging_dir: Path, logging_level: str):
        # Sets up logging configuration

run_procedure()
^^^^^^^^^^^^^^^^

The `run_procedure` method is an abstract method that must be implemented by any class that inherits from `Procedure`. It contains the logic for the specific procedure.

.. code-block:: python

    def run_procedure(self, **kwargs):
        # Custom procedure implementation

Creating a Custom Procedure
----------------------------

To create a custom procedure, extend the `Procedure` class and implement the `run_procedure` method with your specific logic.

Example
^^^^^^^

.. code-block:: python

    from src.yalab_procedures.procedures.procedure import Procedure

    class CustomProcedure(Procedure):
        def run_procedure(self, **kwargs):
            self.logger.info("Running the custom procedure")
            # Custom procedure implementation here
            input_dir = kwargs["input_dir"]
            output_dir = kwargs["output_dir"]


    custom_procedure = CustomProcedure(
        input_directory="path/to/input",
        output_directory="path/to/output",
        logging_directory="path/to/logs",
        logging_level="DEBUG"
    )
    custom_procedure.run()

Using the Procedure Class
-------------------------

1. **Initialize the Procedure**: Provide the required directories and logging configuration.
2. **Implement the `run_procedure` Method**: Define the specific steps of your procedure.
3. **Run the Procedure**: Call the `run` method to execute the procedure.

Example
^^^^^^^

.. code-block:: python

    from src.yalab_procedures.procedures.custom_procedure import CustomProcedure

    procedure = CustomProcedure(
        input_directory="path/to/input",
        output_directory="path/to/output",
        logging_directory="path/to/logs",
        logging_level="INFO"
    )
    procedure.run()

Logging
-------

Logs are saved in the specified logging directory with a timestamped filename. The logging level can be adjusted to control the verbosity of the log output.

Conclusion
----------

The `Procedure` class provides a robust framework for standardizing data preprocessing tasks in your lab. By extending this class, you can create custom procedures that follow a consistent pattern, making it easier to manage and maintain your data processing workflows.

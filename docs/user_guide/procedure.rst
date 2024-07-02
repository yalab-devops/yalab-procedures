Procedure Class
===============

The `Procedure` class is an abstract base class designed to standardize and streamline various data processing tasks. Researchers can extend this class to create custom procedures by implementing the `run_procedure` method.

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

    def __init__(self, **inputs: Any)

Parameters:

- **input_directory** (`Union[str, Path]`): The path to the input directory.
- **output_directory** (`Union[str, Path]`): The path to the output directory.
- **logging_directory** (`Optional[Union[str, Path]]`): The path to the logging directory. Defaults to the output directory if not specified.
- **logging_level** (`str`): The logging level. Default is "INFO".

Methods
-------

### `_run_interface(runtime)`

The `_run_interface` method sets up logging and calls the `run_procedure` method. This method should not be overridden.

.. code-block:: python

    def _run_interface(self, runtime) -> Any:
        # Sets up logging and calls the custom procedure

### `_list_outputs()`

The `_list_outputs` method lists the outputs of the procedure.

.. code-block:: python

    def _list_outputs(self) -> Dict[str, str]:
        # Lists the outputs of the procedure

### `setup_logging()`

The `setup_logging` method sets up the logging configuration, creating a log file in the specified directory.

.. code-block:: python

    def setup_logging(self):
        # Sets up logging configuration

### `run_procedure(**kwargs)`

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
            input_dir = kwargs["input_directory"]
            output_dir = kwargs["output_directory"]

    custom_procedure = CustomProcedure(
        input_directory="path/to/input",
        output_directory="path/to/output",
        logging_directory="path/to/logs",
        logging_level="DEBUG"
    )
    custom_procedure.run()

Defining Custom Inputs and Outputs
----------------------------------

Custom procedures often require specific inputs and produce specific outputs. By defining custom input and output specifications, you can ensure that your procedure receives the necessary parameters and returns the expected results.

### Custom Input Specification

To define custom inputs, create a class that inherits from `ProcedureInputSpec` and add the necessary traits.

.. code-block:: python

    from nipype.interfaces.base import TraitedSpec, File, traits
    from src.yalab_procedures.procedures.procedure import Procedure, ProcedureInputSpec

    class CustomProcedureInputSpec(ProcedureInputSpec):
        custom_input = File(exists=True, mandatory=True, desc="A custom input file")
        custom_param = traits.Str(mandatory=True, desc="A custom parameter")

### Custom Output Specification

To define custom outputs, create a class that inherits from `ProcedureOutputSpec` and add the necessary traits.

.. code-block:: python

    from nipype.interfaces.base import TraitedSpec, File
    from src.yalab_procedures.procedures.procedure import ProcedureOutputSpec

    class CustomProcedureOutputSpec(ProcedureOutputSpec):
        custom_output = File(desc="A custom output file")

### Implementing the Custom Procedure

Extend the `Procedure` class, specify the custom input and output specifications, and implement the `run_procedure` method.

.. code-block:: python

    from src.yalab_procedures.procedures.procedure import Procedure
    from .custom_spec import CustomProcedureInputSpec, CustomProcedureOutputSpec

    class CustomProcedure(Procedure):
        input_spec = CustomProcedureInputSpec
        output_spec = CustomProcedureOutputSpec

        def run_procedure(self, **kwargs):
            self.logger.info("Running the custom procedure")
            input_dir = kwargs["input_directory"]
            output_dir = kwargs["output_directory"]
            custom_input = kwargs["custom_input"]
            custom_param = kwargs["custom_param"]

            # Custom procedure implementation here

            self.logger.info(f"Using custom input: {custom_input}")
            self.logger.info(f"Custom parameter: {custom_param}")

            # Example: Process the custom input and generate a custom output
            custom_output_path = Path(output_dir) / "custom_output.txt"
            with open(custom_output_path, "w") as f:
                f.write(f"Processed {custom_input} with parameter {custom_param}")

            self.outputs["custom_output"] = str(custom_output_path)

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
        logging_level="INFO",
        custom_input="path/to/custom_input.txt",
        custom_param="example_param"
    )
    procedure.run()

Relation to Nipype Interfaces
-----------------------------

The `Procedure` class is designed to mimic the base behavior of Nipype's interfaces, with additional functionalities such as standardized logging and directory validation. If you are familiar with Nipype or if you need further assistance, you can refer to Nipype's documentation.
Specifically, the `Nipype Developer Guide`_ is an excellent resource for understanding how to develop new interfaces and procedures.

Logging
-------

Logs are saved in the specified logging directory with a timestamped filename. The logging level can be adjusted to control the verbosity of the log output.

Conclusion
----------

The `Procedure` class provides a robust framework for standardizing data preprocessing tasks. By extending this class, you can create custom procedures that follow a consistent pattern, making it easier to manage and maintain your data processing workflows.

.. _Nipype Developer Guide: https://nipype.readthedocs.io/en/latest/devel/index.html

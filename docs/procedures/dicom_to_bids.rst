.. _dicom_to_bids_procedure:

DicomToBids Procedure
=====================

The `DicomToBidsProcedure` is a class that converts DICOM files to BIDS format using `HeuDiConv`_.

Overview
--------

The `DicomToBidsProcedure` class extends the `Procedure` class and provides a standardized way to convert DICOM files to BIDS format.

Key Features
------------

- **DICOM to BIDS Conversion**: Uses HeuDiConv to convert DICOM files to BIDS format.
- **Standardized and Robust Heuristic File for YA Lab's MRI Data**: Follows a consistent naming convention for BIDS files.
- **Logging**: Standardized logging setup.

Constructor
-----------

The constructor initializes the procedure with specified directories, subject ID, session ID, and heuristic file.

.. code-block:: python

    def __init__(self, **inputs: Any)

Parameters:

- **input_directory** (`Union[str, Path]`): The path to the input directory containing DICOM files.
- **output_directory** (`Union[str, Path]`): The path to the output directory where BIDS files will be saved.
- **logging_directory** (`Optional[Union[str, Path]]`): The path to the logging directory. Defaults to the output directory if not specified.
- **logging_level** (`str`): The logging level. Default is "INFO".
- **subject_id** (`str`): The subject ID.
- **session_id** (`Optional[str]`): The session ID. Default is None.
- **heuristic_file** (`Union[str, Path]`): The path to the heuristic file. Default : `Default heuristic file for YA Lab's MRI data`_.
- **infer_session_id** (`bool`): Whether to infer the session ID from the input directory. Default is True (won't infer if session ID is provided).

Methods
-------

### `run_procedure(**kwargs)`

The `run_procedure` method contains the actual implementation of the procedure,
including formatting the command to run `HeuDiConv` based on the given inputs and executing it.

.. code-block:: python

    def run_procedure(self, **kwargs):
        self.logger.info("Running DicomToBidsProcedure")
        self.logger.debug(f"Input attributes: {kwargs}")

        # Run the heudiconv command
        command = self.build_commandline()
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
        self.logger.info("Finished running DicomToBidsProcedure")

### `build_commandline()`

.. code-block:: python

    def build_commandline(self):
        # Build the command line arguments
        cmd_args = self._parse_inputs()
        cmd = [self._cmd] + cmd_args
        self.logger.debug(f"Command line: {' '.join(cmd)}")
        # Run the command
        return " ".join(cmd)


### `infer_session_id()`

The `infer_session_id` method infers the session ID from the input directory based on the naming convention provided by `TAU's MRI center`_.

.. code-block:: python

    def infer_session_id(self):
        """
        Infer the session ID from the input directory name.
        This is useful for DICOM directories provided by TAU's MRI facility.
        """
        if not isdefined(self.inputs.session_id) and self.inputs.infer_session_id:
            session_id = Path(self.inputs.input_directory).name.split("_")[-2:]
            session_id = "".join(session_id)
            self.inputs.session_id = session_id




Using the DicomToBidsProcedure Class
-------------------------------------

1. **Initialize the Procedure**: Provide the required directories and logging configuration.
2. **Implement the `run_procedure` Method**: Define the specific steps of your procedure.
3. **Run the Procedure**: Call the `run` method to execute the procedure.

Example
^^^^^^^

.. code-block:: python

    >>> from yalab_procedures.procedures.dicom_to_bids import DicomToBidsProcedure
    >>> dcm2bids = DicomToBidsProcedure()
    >>> dcm2bids.inputs.input_directory = '/path/to/dicom' # Scanning session's DICOM directory
    >>> dcm2bids.inputs.output_directory = '/path/to/bids' # BIDS output directory
    >>> dcm2bids.inputs.subject_id = '01' # Subject ID
    >>> dcm2bids.inputs.session_id = '01' # Session ID
    >>> dcm2bids.inputs.heuristic_file = '/path/to/heuristic.py'
    >>> dcm2bids.inputs.cmdline
    'heudiconv -s 01 -ss 01 -f /path/to/heuristic.py --files /path/to/dicom/*/*.dcm -o /path/to/bids -c dcm2niix --overwrite --bids'
    >>> res = dcm2bids.run()  # doctest: +SKIP

Logging
-------

Logs are saved in the specified logging directory with a timestamped filename. The logging level can be adjusted to control the verbosity of the log output.

Conclusion
----------

The `DicomToBidsProcedure` class provides a robust framework for converting DICOM files to BIDS format. By extending this class, you can create custom procedures that follow a consistent pattern, making it easier to manage and maintain your data processing workflows.

.. _`HeuDiConv`: https://heudiconv.readthedocs.io/en/latest/
.. _`Default heuristic file for YA Lab's MRI data`: https://github.com/yalab-devops/yalab-procedures/blob/main/src/yalab_procedures/procedures/dicom_to_bids/templates/heuristic.py
.. _`TAU's MRI center`: https://mri.tau.ac.il/

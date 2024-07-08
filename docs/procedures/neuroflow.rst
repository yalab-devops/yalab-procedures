.. _neuroflow_procedure:

Neuroflow Procedure
===================

The `NeuroflowProcedure` is a class that orchestrates the processing of MRI data using the `neuroflow` suite, tailored for advanced analyses including structural and diffusion MRI processing pipelines.

Overview
--------

The `NeuroflowProcedure` class extends the `Procedure` class, providing an automated process for executing various neuroimaging analysis steps facilitated by the `neuroflow` tool.

Key Features
------------

- **Comprehensive MRI Processing**: Leverages the neuroflow suite to process MRI data extensively.
- **Customizable Processing Steps**: Enables selective execution of processing steps such as `sMRIPrep`, tensor models, connectome reconstruction, etc.
- **Integration with Cloud Services**: Utilizes Google Cloud services for collection of additional information for YA-Lab's participants, requiring Google credentials.
- **Flexible Configuration**: Supports a variety of configurations through command line arguments to tailor the processing pipeline.

Constructor
-----------

The constructor initializes the procedure with specified directories, credentials, and processing parameters.

.. code-block:: python

    def __init__(self, **inputs: Any)

Parameters:

- **input_directory** (`Union[str, Path]`): The directory containing preprocessed MRI data.
- **output_directory** (`Union[str, Path]`): The directory where the Neuroflow outputs will be saved.
- **google_credentials** (`Union[str, Path]`): Path to the Google Cloud credentials file, necessary for processing steps that interface with Google services.
- **patterns_file** (`Union[str, Path]`, optional): Path to a patterns file which contains mapping of required inputs for different processing steps.
- **atlases** (`List[str]`, optional): A list of atlases to use for various processing steps, specified as strings. For example, `["fan2016", "huang2022"]`.
- **crop_to_gm** (`bool`, optional): Whether to crop the atlases to the gray matter, enhancing focus on relevant brain structures. Defaults to `True`.
- **use_smriprep** (`bool`, optional): Indicates whether sMRIPrep should be used for the registration of atlases and preprocessing of structural data. Defaults to `True`.
- **fs_license_file** (`Union[str, Path]`, optional): Path to the FreeSurfer license file, required if FreeSurfer steps are involved in the pipeline.
- **max_bval** (`int`, optional): Maximum b-value to use for diffusion tensor imaging (DTI) calculations. Defaults to `1000`.
- **ignore_steps** (`List[str]`, optional): List of processing steps to ignore. This allows skipping specified steps, useful in re-running or customizing the workflow.
- **steps** (`List[str]`, optional): List of specific steps to execute, providing control over which parts of the full pipeline are run.
- **force** (`bool`, optional): Force the re-running of all steps, even if outputs already exist. Useful for ensuring a fresh processing run. Defaults to `False`.


Methods
-------

### `run_procedure()`

Executes the configured Neuroflow pipeline.

.. code-block:: python

    def run_procedure(self):
        """
        Run the DicomToBidsProcedure

        Raises
        ------
        CalledProcessError
            If the command fails to run. The error message will be logged.
        """

        self.logger.info("Running NeuroflowProcedure")
        self.logger.debug(f"Input attributes: {kwargs}")

        # Run the heudiconv command
        command = self.cmdline
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
        self.logger.info("Finished running NeuroflowProcedure")

Using the NeuroflowProcedure Class
----------------------------------

1. **Initialize the Procedure**: Provide the required directories, credentials, and configuration.
2. **Configure the Procedure**: Set the necessary inputs such as atlases and processing steps.
3. **Run the Procedure**: Execute the procedure using the `run` method.

Example
^^^^^^^

.. code-block:: python

    >>> from yalab_procedures.procedures.neuroflow import NeuroflowProcedure
    >>> neuroflow = NeuroflowProcedure()
    >>> neuroflow.inputs.input_directory = '/path/to/preprocessed/data'
    >>> neuroflow.inputs.output_directory = '/path/to/neuroflow/output'
    >>> neuroflow.inputs.google_credentials = '/path/to/google_credentials.json'
    >>> neuroflow.inputs.atlases = ["fan2016", "huang2022"]
    >>> res = neuroflow.run()  # doctest: +SKIP

Logging
-------

Logs are saved in the specified logging directory with a timestamped filename. The logging level can be adjusted to control the verbosity of the log output.

Conclusion
----------

The `NeuroflowProcedure` class provides a robust and flexible framework for extending MRI data processing capabilities. By leveraging the `neuroflow` suite, researchers can perform comprehensive analyses on structural and diffusion MRI data efficiently.

.. _`neuroflow`: https://neuroflow.readthedocs.io/en/latest/

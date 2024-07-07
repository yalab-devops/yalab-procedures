.. _MRTrix Preprocessing Procedure:

Mrtrix Preprocessing Procedure
===============================

The `MrtrixPreprocessingProcedure` is a class that applies several preprocessing algorithms to dMRI data.
You can read more about the MRtrix software package `here <https://mrtrix.readthedocs.io/en/latest/>`__, and specifically on the preprocessing steps `here <https://github.com/RonnieKrup/ComisCorticalCode>`_.

Overview
--------

The `MrtrixPreprocessingProcedure` class extends the `Procedure` class and provides a standardized way to preprocess dMRI data using MRtrix. The class includes methods for running the preprocessing steps, building the command line arguments, and logging the output.

Key Features
------------

- **Inputs Preparation**: Standardized input preparation for MRtrix preprocessing as required by the `ComisCorticalCode`_.
- **Standardized Handling of Inputs/Outputs**: Consistent handling of input and output directories via `nipype's BaseInterfaceInputSpec`_.
- **Automatic Setup of the `ComisCorticalCode`_ Executable**: Automatically sets up the `ComisCorticalCode` (cloning from the `static git destination <https://github.com/RonnieKrup/ComisCorticalCode>`_ and setting up the correct path).
- **Command Line Building and Execution**: Building the command line arguments and executing the MRtrix preprocessing steps.
- **Logging**: Standardized logging setup.

Constructor
-----------

The constructor initializes the procedure with specified directories and configuration file.

.. code-block:: python

    def __init__(self, **inputs: Any)

Parameters:

- **input_directory** (`Union[str, Path]`): The path to the input BIDS-appropriate directory containing dMRI data.
- **output_directory** (`Union[str, Path]`): The path to the output directory where preprocessed data will be saved.
- **work_directory** (`Union[str, Path]`): The path to the working directory where intermediate files will be saved.
- **config_file** (`Union[str, Path]`): The path to the `configuration file <https://github.com/RonnieKrup/ComisCorticalCode/blob/master/template_files/config_template.json>`_ for the preprocessing steps.
- **logging_directory** (`Optional[Union[str, Path]]`): The path to the logging directory. Defaults to the output directory if not specified.
- **logging_level** (`str`): The logging level. Default is "INFO".

Methods
-------

### `run_procedure(**kwargs)`

The `run_procedure` method contains the actual implementation of the procedure,
including the location of required files, preparation in the form required by the associated executable, and formation of the command to run MRtrix preprocessing based on the given inputs and executing it.

.. code-block:: python

    def run_procedure(self, **kwargs):
        """
        Run the MRtrix preprocessing procedure
        """
        self.logger.info("Starting MRtrix preprocessing procedure...")
        self.logger.info("Validating Comis cortical executable.")
        self.validate_comis_cortical_exec()
        self.logger.info("Inferring additional inputs.")
        self.set_missing_inputs()
        self.logger.info("Initiating workflow for preparing inputs.")
        wf = self.initiate_prepare_inputs_workflow()
        wf.run()
        self.logger.info("Running preprocessing workflow.")
        comis_cortical = init_comis_cortical_wf(wf)
        comis_cortical.run()

### `initiate_prepare_inputs_workflow()`

The `initiate_prepare_inputs_workflow` method initiates the MRtrix preprocessing workflow.
It is composed of two sub-workflows: `init_mrtrix_preprocessing_wf` and `init_comis_cortical_wf`, which govern the preparation of inputs and the actual preprocessing steps, respectively.

.. code-block:: python

    def initiate_prepare_inputs_workflow(self):
        """
        Initiate the MRtrix preprocessing workflow

        Returns
        -------
        wf : pe.Workflow
            The MRtrix preprocessing workflow
        """
        wf = init_mrtrix_preprocessing_wf(self._gen_wf_name())
        if isdefined(self.inputs.work_directory):
            wf.base_dir = self.inputs.work_directory
        wf.inputs.inputnode.input_directory = self.inputs.input_directory
        wf.inputs.inputnode.subject_id = self.inputs.subject_id
        wf.inputs.inputnode.session_id = self.inputs.session_id
        wf.inputs.inputnode.comis_cortical_exec = self.inputs.comis_cortical_exec
        wf.inputs.inputnode.config_file = self.inputs.config_file
        wf.inputs.inputnode.output_directory = self.inputs.output_directory
        return wf


### `validate_comis_cortical_exec()`

The `validate_comis_cortical_exec` method validates the Comis cortical executable.

.. code-block:: python

    def validate_comis_cortical_exec(self):
        """
        Validate the Comis cortical executable
        """
        if not isdefined(self.inputs.comis_cortical_exec):
            self.logger.info("Comis cortical executable not provided.")
            self.inputs.comis_cortical_exec = self._download_comis_cortical_exec()

### `_download_comis_cortical_exec()`

The `_download_comis_cortical_exec` method downloads the Comis cortical executable.

.. code-block:: python

    def _download_comis_cortical_exec(self):
        """
        Download the Comis cortical executable
        """
        self.logger.info("Downloading Comis cortical executable.")
        comis_cortical_repo = self._clone_comis_cortical_repo()
        self.logger.info("Comis cortical executable downloaded.")
        comis_cortical_exec = self.comis_cortical_exec_default_destination.format(
            repo=comis_cortical_repo
        )
        if not Path(comis_cortical_exec).exists():
            raise FileNotFoundError(
                f"Comis cortical executable not found at {comis_cortical_exec}"
            )
        else:
            self.logger.info(
                f"Comis cortical executable found at {comis_cortical_exec}"
            )
        return comis_cortical_exec

### `_clone_comis_cortical_repo()`

The `_clone_comis_cortical_repo` method clones the Comis cortical repository.

.. code-block:: python

    def _clone_comis_cortical_repo(self):
        """
        Clone the Comis cortical repository
        """
        comis_cortical_repo = Path(self.inputs.work_directory) / "ComisCorticalCode"
        nipype_logging.getLogger("nipype.workflow").info(
            f"Cloning Comis cortical repository to {comis_cortical_repo}"
        )
        comis_cortical_repo = comis_cortical_repo.resolve()
        if not comis_cortical_repo.exists():
            git.Git(comis_cortical_repo.parent).clone(self.comis_cortical_github)
            self.logger.info("Comis cortical repository cloned.")

        return comis_cortical_repo

Using the DicomToBidsProcedure Class
-------------------------------------

.. code-block:: python

    >>> from yalab_procedures.procedures.mrtrix_preprocessing import MrtrixPreprocessingProcedure
    >>> mrtrix_preprocessing = MrtrixPreprocessingProcedure(
    >>> mrtrix_preprocessing.inputs.input_directory='/path/to/bids',  # BIDS input directory
    >>> mrtrix_preprocessing.inputs.output_directory='/path/to/preprocessed',  # Preprocessed output directory
    >>> mrtrix_preprocessing.inputs.work_directory='/path/to/work',  # Working directory
    >>> mrtrix_preprocessing.inputs.config_file='/path/to/config.json',  # Configuration file
    >>> mrtrix_preprocessing.inputs.logging_directory='/path/to/logs',  # Logging directory
    >>> mrtrix_preprocessing.inputs.logging_level='INFO'  # Logging level
    >>> res = mrtrix_preprocessing.run()  # doctest: +SKIP

Logging
-------

Logs are saved in the specified logging directory with a timestamped filename. The logging level can be adjusted to control the verbosity of the log output.

Conclusion
----------

The `DicomToBidsProcedure` class provides a robust framework for converting DICOM files to BIDS format. By extending this class, you can create custom procedures that follow a consistent pattern, making it easier to manage and maintain your data processing workflows.

.. _`ComisCorticalCode`: https://github.com/RonnieKrup/ComisCorticalCode
.. _`nipype's BaseInterfaceInputSpec`: https://nipype.readthedocs.io/en/latest/devel/interface_specs.html

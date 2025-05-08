.. _neuroflow_procedure:

Neuroflow Procedure
===================

The `AxsiProcedure` is a class that orchestrates the processing of MRI data using the `AxSI` package.

Overview
--------

The `AxsiProcedure` class extends the `Procedure` class, providing an automated process for executing various neuroimaging analysis steps facilitated by the `AxSI` package.

Constructor
-----------

The constructor initializes the procedure with specified directories, credentials, and processing parameters.

.. code-block:: python

    def __init__(self, **inputs: Any)

Parameters
----------

- **output_directory** (``Union[str, Path]``):
  The directory where AxSI's output will be stored. This directory does not need to exist beforehand and is mandatory.

- **run_name** (``str``):
  The name assigned to the run. This is a mandatory parameter that helps identify the specific execution instance.

- **data** (``Union[str, Path]``):
  Path to the data file. This file must exist and is required for processing.

- **mask** (``Union[str, Path]``):
  Path to the mask file. This file must exist and is mandatory for the operation.

- **bval** (``Union[str, Path]``):
  Path to the bval file, which must exist. This file is necessary for the processing steps.

- **bvec** (``Union[str, Path]``):
  Path to the bvec file. This file must exist and is required for the procedure.

- **small_delta** (``float``, optional):
  Specifies the gradient duration in milliseconds. Defaults to ``15.0``.

- **big_delta** (``float``, optional):
  Defines the time interval for scanning in milliseconds. Defaults to ``45.0``.

- **gmax** (``float``, optional):
  The maximum amplitude of the gradient in G/cm. Defaults to ``7.9``.

- **gamma_val** (``int``, optional):
  The gyromagnetic ratio, with a default value of ``4257``.

- **num_processes_pred** (``int``, optional):
  Number of processes to run in parallel during the prediction step. Defaults to ``1``.

- **num_threads_pred** (``int``, optional):
  Number of threads to run in parallel during the prediction step. Defaults to ``1``.

- **num_processes_axsi** (``int``, optional):
  Number of processes to run in parallel during the AxSI step. Defaults to ``1``.

- **num_threads_axsi** (``int``, optional):
  Number of threads to run in parallel during the AxSI step. Defaults to ``1``.

- **nonlinear_lsq_method** (``str``, optional):
  Method for nonlinear least squares. Options include ``'R-minpack'``, ``'scipy'``, or ``'lsq-axsi'``. Defaults to ``'R-minpack'``.

- **linear_lsq_method** (``str``, optional):
  Method for linear least squares. Options include ``'R-quadprog'``, ``'gurobi'``, ``'scipy'``, or ``'cvxpy'``. Defaults to ``'R-quadprog'``.

- **debug_mode** (``bool``, optional):
  Enables debug mode if set to ``True``. Defaults to ``False``.

Methods
-------

### `run_procedure()`

Executes the configured AxSI analysis.

.. code-block:: python

    def run_procedure(self):
        """
        Run the AxsiProcedure

        Raises
        ------
        CalledProcessError
            If the command fails to run. The error message will be logged.
        """

        self.logger.info("Running AxsiProcedure")
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
        self.logger.info("Finished running AxsiProcedure")


### `build_commandline()`

.. code-block:: python

    def build_commandline(self) -> str:
        # Build the command line arguments
        cmd_args = self._parse_inputs()
        cmd = [self._cmd] + cmd_args
        self.logger.debug(f"Command line: {' '.join(cmd)}")
        # Run the command
        return " ".join(cmd) and `infer_subject_id()`

### `infer_session_id()` and `infer_subject_id()`

If the --run-name parameter is not specified, it will be derived from the path of the data file using the `infer_session_id` and `infer_subject_id` from the path of the input file based on the naming convention provided by `TAU's MRI center`_.

For example, if the input directory is: /home/PreProcessing/bids/sub-DH080922/ses-202211101731/dwi/data.nii.gz, then:

subject_id = DH080922
session_id = 202211101731

Thus, the inferred --run-name will be:
--run-name = "DH080922_202211101731"

.. code-block:: python

    def infer_subject_id(self) -> str:
        parts = Path(self.inputs.data).parts
        for part in parts:
            if part.startswith("sub-"):
                return part.split("-")[-1]
        raise IDNotFoundError("Subject ID not found in the path of the input file.")

    def infer_session_id(self) -> str:
        parts = Path(self.inputs.data).parts
        for part in parts:
            if part.startswith("ses-"):
                return part.split("-")[-1]
        raise IDNotFoundError("Session ID not found in the path of the input file.")

Using the AxsiProcedure Class
----------------------------------

1. **Initialize the Procedure**: Provide the required directories and missing parameters.
2. **Run the Procedure**: Execute the procedure using the `run` method.

Example
^^^^^^^

.. code-block:: python

     >>> from yalab_procedures.procedures.axsi import AxsiProcedure
    >>> axsi = AxsiProcedure()
    >>> axsi.inputs.output_directory = "/path/to/axsi/output"
    >>> axsi.inputs.run_name = "subject_id-session_id"
    >>> axsi.inputs.data = "/path/to/data_nii_input_file"
    >>> axsi.inputs.mask = "/path/to/mask_nii_input_file"
    >>> axsi.inputs.bval = "/path/to/bval_input_file"
    >>> axsi.inputs.bvec = "/path/to/bvec_input_file"
    >>> axsi.inputs.linear_lsq_method = "lsq-axsi"
    >>> axsi.inputs.nonlinear_lsq_method = "gurobi"
    >>> axsi.inputs.num_processes_pred = 35
    >>> axsi.inputs.num_processes_axsi = 35
    >>> axsi.inputs.debug_mode = True
    >>> axsi.inputs.cmdline
    'axsi-main.py ' \
                                   '--subj-folder /path/to/axsi/output' \
                                   '--run-name "subject_id-session_id"' \
                                   '--bval "/path/to/bval_input_file" ' \
                                   '--bvec "/path/to/bvec_input_file" ' \
                                   '--data "/path/to/data_nii_input_file" ' \
                                   '--mask "/path/to/mask_nii_input_file" ' \
                                   '--nonlinear-lsq-method lsq-axsi ' \
                                   '--linear-lsq-method gurobi ' \
                                   '--num-processes-pred 35' \
                                   '--num-processes-axsi 35' \
                                   '--debug-mode '
    >>> res = axsi.run()

Logging
-------

Logs are saved in the specified logging directory with a timestamped filename. The logging level can be adjusted to control the verbosity of the log output.

Conclusion
----------

The `AxsiProcedure` class provides a robust and flexible framework for extending MRI data processing capabilities. By leveraging the `AxSI` package, researchers can perform comprehensive analyses on structural and diffusion MRI data efficiently.

.. _`AxSI`: https://axsi.readthedocs.io/en/latest/

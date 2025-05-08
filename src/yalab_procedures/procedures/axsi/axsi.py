# src/yalab_procedures/procedures/axsi/axsi.py

from pathlib import Path
from subprocess import CalledProcessError, run

from nipype.interfaces.base import (
    CommandLine,
    CommandLineInputSpec,
    Directory,
    File,
    traits,
    isdefined,
)

from yalab_procedures.procedures.base.procedure import (
    Procedure,
    ProcedureInputSpec,
    ProcedureOutputSpec,
)


class IDNotFoundError(Exception):
    """Custom exception raised when an ID is not found in the input directory."""
    pass


class AxsiInputSpec(ProcedureInputSpec, CommandLineInputSpec):
    """
    Input specification for the AxSI
    """
    output_directory = Directory(
        exists=False,
        mandatory=True,
        argstr="--subj-folder %s",
        position=0,
        desc="Directory to store AxSI's output",
    )
    run_name = traits.Str(
        argstr="--run-name %s",
        desc="Specify the name for the run",
        mandatory=True,
        position=1,
    )
    data = File(
        exists=True,
        mandatory=True,
        argstr="--data %s",
        desc="Path to the data file",
        position=2,
    )
    mask = File(
        exists=True,
        mandatory=True,
        argstr="--mask %s",
        desc="Path to the mask file",
        position=3,
    )
    bval = File(
        exists=True,
        mandatory=True,
        argstr="--bval %s",
        desc="Path to the bval file",
        position=4,
    )
    bvec = File(
        exists=True,
        mandatory=True,
        argstr="--bvec %s",
        desc="Path to the bvec file",
        position=5,
    )
    small_delta = traits.Float(
        argstr="--small-delta %f",
        desc="Gradient duration in milliseconds",
        default_value=15.0,
        usedefault=True,
        position=6,
    )
    big_delta = traits.Float(
        argstr="--big-delta %f",
        desc="Time to scan (time interval) in milliseconds",
        default_value=45.0,
        usedefault=True,
        position=7,
    )
    gmax = traits.Float(
        argstr="--gmax %f",
        desc="Gradient maximum amplitude in G/cm",
        default_value=7.9,
        usedefault=True,
        position=8,
    )
    gamma_val = traits.Int(
        argstr="--gamma-val %d",
        desc="Gyromagnetic ratio",
        default_value=4257,
        usedefault=True,
        position=9,
    )
    num_processes_pred = traits.Int(
        argstr="--num-processes-pred %d",
        desc="Number of processes to run in parallel in prediction step",
        default_value=1,
        usedefault=True,
        position=10,
    )
    num_threads_pred = traits.Int(
        argstr="--num-threads-pred %d",
        desc="Number of threads to run in parallel in prediction step",
        default_value=1,
        usedefault=True,
        position=11,
    )
    num_processes_axsi = traits.Int(
        argstr="--num-processes-axsi %d",
        desc="Number of processes to run in parallel in AxSI step",
        default_value=1,
        usedefault=True,
        position=12,
    )
    num_threads_axsi = traits.Int(
        argstr="--num-threads-axsi %d",
        desc="Number of threads to run in parallel in AxSI step",
        default_value=1,
        usedefault=True,
        position=13,
    )
    nonlinear_lsq_method = traits.Enum(
        "R-minpack", "scipy", "lsq-axsi",
        argstr="--nonlinear-lsq-method %s",
        desc="Method for linear least squares. Choose from 'R-minpack', 'scipy', or 'lsq-axsi'.",
        default="R-minpack",
        usedefault=True,
        position=14,
    )
    linear_lsq_method = traits.Enum(
        "R-quadprog", "gurobi", "scipy", "cvxpy",
        argstr="--linear-lsq-method %s",
        desc="Method for linear least squares. Choose from 'R-quadprog', 'gurobi', 'scipy', or 'cvxpy'.",
        default="R-quadprog",
        usedefault=True,
        position=15,
    )
    debug_mode = traits.Bool(
        argstr="--debug-mode",
        desc="Enable debug mode (default is disabled).",
        default_value=False,
        usedefault=True,
        position=16,
    )


class AxsiOutputSpec(ProcedureOutputSpec):
    """
    Output specification for the AxSI
    """

    output_directory = Directory(desc="Output directory containing AxSI's output")
    CMDfh_out_file = File()
    CMDfr_out_file = File()
    dt_out_file = File()
    eigval_out_file = File()
    eigvec_out_file = File()
    fa_out_file = File()
    md_out_file = File()
    pasi_out_file = File()
    paxsi_out_file = File()
    pcsf_out_file = File()
    pfr_out_file = File()
    ph_out_file = File()


class AxsiProcedure(Procedure, CommandLine):
    """
    Perform advanced processing of diffusion MRI (dMRI) and structural data using `AxSI <https://pypi.org/project/AxSI/>`_.

    If the run_name is not specified, it will be derived from the path of the data file.

    For example, if the input directory is: /home/PreProcessing/bids/sub-DH080922/ses-202211101731/dwi/data.nii.gz, then:

    subject_id = DH080922
    session_id = 202211101731

    Thus, the inferred --run-name will be:
    --run-name = "DH080922_202211101731"

    Examples
    --------
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
    'axsi-main ' \
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
    >>> res = axsi.run() # doctest: +SKIP

    """

    _cmd = "axsi-main"
    input_spec = AxsiInputSpec
    output_spec = AxsiOutputSpec
    _version = "0.0.1"

    def __init__(self, **inputs):
        super(AxsiProcedure, self).__init__(**inputs)

    def run_procedure(self, **kwargs):
        """
        Run the AxsiProcedure

        Raises
        ------
        CalledProcessError
            If the command fails to run. The error message will be logged.
        """

        self.logger.info("Running AxsiProcedure")
        self.logger.debug(f"Input attributes: {kwargs}")
        self.set_missing_inputs()

        if not self.cmdline:
            command = self.build_commandline()
        else:
            command = self.cmdline

        # Run the axsi command
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

    def build_commandline(self) -> str:
        """
        Build the command line arguments for the axsi command

        Returns
        -------
        str
            The command line arguments as a string
        """
        # Build the command line arguments
        cmd_args = self._parse_inputs()
        cmd = [self._cmd] + cmd_args
        self.logger.debug(f"Command line: {' '.join(cmd)}")
        # Run the command
        return " ".join(cmd)

    def set_missing_inputs(self):
        """
        Set missing inputs for the AxSI procedure
        """
        if not isdefined(self.inputs.run_name):
            subject_id = self.infer_subject_id()
            session_id = self.infer_session_id()
            self.inputs.run_name = "_".join([subject_id, session_id])

    def infer_subject_id(self) -> str:
        """
        Infer the subject ID from the path of the input file.

        Returns
        -------
        str
            The subject ID.

        Raises
        ------
        IDNotFoundError
            If the subject ID is not found in the path of the input file.
        """
        # Get the parts of the path
        parts = Path(self.inputs.data).parts

        # Search for the subject ID in all parts
        for part in parts:
            if part.startswith("sub-"):
                return part.split("-")[-1]

        raise IDNotFoundError("Subject ID not found in the path of the input file.")

    def infer_session_id(self) -> str:
        """
        Infer the session ID from the path of the input file.

        Returns
        -------
        str
            The session ID.

        Raises
        ------
        IDNotFoundError
            If the session ID is not found in the path of the input file.
        """
        # Get the parts of the path
        parts = Path(self.inputs.data).parts

        # Search for the session ID in all parts
        for part in parts:
            if part.startswith("ses-"):
                return part.split("-")[-1]

        raise IDNotFoundError("Session ID not found in the path of the input file.")

    def _list_outputs(self):
        """
        List the outputs of the AxsiProcedure

        Returns
        -------
        dict
            The outputs of the procedure
        """
        outputs = self._outputs().get()
        outputs["output_directory"] = (Path(self.inputs.output_directory) / self.inputs.run_name).as_posix()
        outputs["CMDfh_out_file"] = (
                Path(self.inputs.output_directory) / self.inputs.run_name / "CMDfh.nii.gz").as_posix()
        outputs["CMDfr_out_file"] = (
            Path(self.inputs.output_directory) / self.inputs.run_name / "CMDfr.nii.gz").as_posix()
        outputs["dt_out_file"] = (Path(self.inputs.output_directory) / self.inputs.run_name / "dt.nii.gz").as_posix()
        outputs["eigval_out_file"] = (
            Path(self.inputs.output_directory) / self.inputs.run_name / "eigval.nii.gz").as_posix()
        outputs["eigvec_out_file"] = (
            Path(self.inputs.output_directory) / self.inputs.run_name / "eigvec.nii.gz").as_posix()
        outputs["fa_out_file"] = (Path(self.inputs.output_directory) / self.inputs.run_name / "fa.nii.gz").as_posix()
        outputs["md_out_file"] = (Path(self.inputs.output_directory) / self.inputs.run_name / "md.nii.gz").as_posix()
        outputs["pasi_out_file"] = (
            Path(self.inputs.output_directory) / self.inputs.run_name / "pasi.nii.gz").as_posix()
        outputs["paxsi_out_file"] = (
            Path(self.inputs.output_directory) / self.inputs.run_name / "paxsi.nii.gz").as_posix()
        outputs["pcsf_out_file"] = (
            Path(self.inputs.output_directory) / self.inputs.run_name / "pcsf.nii.gz").as_posix()
        outputs["pfr_out_file"] = (Path(self.inputs.output_directory) / self.inputs.run_name / "pfr.nii.gz").as_posix()
        outputs["ph_out_file"] = (Path(self.inputs.output_directory) / self.inputs.run_name / "ph.nii.gz").as_posix()

        return outputs

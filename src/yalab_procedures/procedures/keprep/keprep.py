import os
from pathlib import Path
from typing import Any

from keprep import config
from keprep.config import init_spaces
from keprep.workflows.base.workflow import init_keprep_wf
from nipype.interfaces.base import Directory, File, isdefined, traits

from yalab_procedures.procedures.base.procedure import (
    Procedure,
    ProcedureInputSpec,
    ProcedureOutputSpec,
)
from yalab_procedures.procedures.keprep.templates.inputs import INPUTS_MAPPING


class KePrepInputSpec(ProcedureInputSpec):
    """
    Input specification for the KePrepProcedure
    """

    # Execution configuration
    input_directory = Directory(
        exists=True,
        mandatory=True,
        desc="Input directory containing preprocessed data",
    )
    output_directory = Directory(
        exists=False,
        mandatory=True,
        desc="A path where anatomical derivatives are found to fast-track *sMRIPrep*.",
    )
    anat_derivatives = Directory(
        exists=False,
        mandatory=False,
        desc="Directory to store anatomical derivatives",
    )
    bids_database_dir = Directory(
        exists=False,
        mandatory=False,
        desc="Directory containing SQLite database indices for the input BIDS dataset.",
    )
    bids_filters = traits.File(
        exists=True,
        argstr="-v %s:/bids_filters.json",
        desc="BIDS filter file",
    )
    reset_database = traits.Bool(
        True,
        usedefault=True,
        desc="Whether to reset the database",
    )
    fs_license_file = File(
        exists=True,
        mandatory=False,
        desc="Path to FreeSurfer license file",
    )
    fs_subjects_dir = Directory(
        exists=False,
        mandatory=False,
        desc="Path to FreeSurfer subjects directory",
    )
    participant_label = traits.List(
        traits.Str,
        argstr="--participant_label %s",
        desc="Participant label",
        sep=",",
    )
    work_directory = Directory(
        exists=False,
        mandatory=True,
        argstr="-v %s:/work",
        desc="Path to work directory",
    )
    output_spaces = traits.List(
        traits.Str,
        argstr="--output-spaces %s",
        desc="Output spaces",
        sep=",",
    )
    # Workflow configuration
    anat_only = traits.Bool(
        False,
        usedefault=True,
        desc="Whether to run anatomical processing only",
    )
    dwi2t1w_dof = traits.Int(
        6,
        usedefault=True,
        desc="Degrees of freedom for the DWI-to-T1w registration",
    )
    dwi2t1w_init = traits.Str(
        "header",
        usedefault=True,
        desc="Initialization for the DWI-to-T1w registration",
    )
    do_reconall = traits.Bool(
        True,
        usedefault=True,
        desc="Whether to run FreeSurfer recon-all",
    )
    longitudinal = traits.Bool(
        True,
        argstr="--longitudinal",
        desc="Longitudinal processing. May increase runtime.",
    )
    skull_strip_fixed_seed = traits.Bool(
        False,
        usedefault=True,
        desc="Whether to use a fixed seed for skull stripping",
    )
    skull_strip_template = traits.Str(
        "OASIS30ANTs",
        usedefault=True,
        desc="Template for skull stripping",
    )
    hires = traits.Bool(
        True,
        usedefault=True,
        desc="Whether to run the high-resolution workflow",
    )
    # Nipype configuration
    crashfile_format = traits.Enum(
        "txt",
        "txt.gz",
        "no",
        usedefault=True,
        desc="Crashfile format",
    )
    nprocs = traits.Int(
        os.cpu_count(),
        usedefault=True,
        desc="Number of processes (compute tasks) that can be run in parallel (multiprocessing only).",
    )
    omp_nthreads = traits.Int(
        1,
        usedefault=True,
        desc="Number of CPUs a single process can access for multithreaded execution.",
    )
    stop_on_first_crash = traits.Bool(
        False,
        usedefault=True,
        desc="Whether to stop on first crash",
    )
    force = traits.Bool(
        False,
        usedefault=True,
        desc="Whether to force the procedure to run even if the output directory already exists.",
    )


class KePrepOutputSpec(ProcedureOutputSpec):
    """
    Output specification for the SmriprepProcedure
    """

    # T1w-related files
    preprocessed_T1w = File(desc="Preprocessed T1w image")
    brain_mask = File(desc="Brain mask")
    MNI_preprocessed_T1w = File(desc="MNI preprocessed T1w image")
    MNI_brain_mask = File(desc="MNI brain mask")
    # Transformations
    mni_to_native_transform = File(desc="MNI to native transform")
    native_to_mni_transform = File(desc="Native to MNI transform")
    fsnative_to_native_transform = File(desc="Freesurfer native to native transform")
    native_to_fsnative_transform = File(desc="Native to freesurfer native transform")
    # Segmentation
    segmentation = File(desc="Segmentation")
    probseg_gm = File(desc="Probabilistic segmentation of gray matter")
    probseg_wm = File(desc="Probabilistic segmentation of white matter")
    probseg_csf = File(desc="Probabilistic segmentation of cerebrospinal fluid")
    # FreeSurfer
    fs_fsaverage = File(desc="fsaverage")
    fs_T1w = File(desc="T1w")
    fs_brainmask = File(desc="Brain mask")
    fs_brain = File(desc="Dilated brain mask")
    fs_wm = File(desc="White matter")
    fs_lh_pial = File(desc="Left hemisphere pial surface")
    fs_rh_pial = File(desc="Right hemisphere pial surface")


class KePrepProcedure(Procedure):
    """
    Procedure for running Smriprep
    """

    input_spec = KePrepInputSpec
    output_spec = KePrepOutputSpec
    _version = "0.0.1"

    def __init__(self, **inputs: Any):
        super().__init__(**inputs)

    def _setup_config_toml(self):
        """
        Set up the configuration file
        """
        inputs_dict = self.inputs.get()
        configuration_dict = {}
        for key, value in inputs_dict.items():
            if key in INPUTS_MAPPING:
                target_key = INPUTS_MAPPING.get(key)
                if not isdefined(value):
                    default_value = self._get_default_value(key)
                    if isdefined(default_value):
                        configuration_dict[target_key] = default_value
                    else:
                        raise ValueError(f"Value for {key} not provided.")
                else:
                    configuration_dict[target_key] = value
            else:
                if isdefined(value):
                    configuration_dict[key] = value
        return configuration_dict

    def _get_default_value(self, key: str) -> Any:
        """
        Get the default value of an input
        """
        value = getattr(self.inputs, key)
        return value if isdefined(value) else self.inputs.traits().get(key).default

    def run_procedure(self, **kwargs):
        """
        Run the SmriprepProcedure

        Raises
        ------
        CalledProcessError
            If the command fails to run. The error message will be logged.
        """

        self.logger.info("Running SmriprepProcedure")
        self.logger.debug(f"Input attributes: {kwargs}")

        # Locate the FreeSurfer license file
        self._locate_fs_license_file()
        # Prepare inputs
        configuration_dict = self._setup_config_toml()
        config.from_dict(configuration_dict)
        init_spaces()

        # Run the workflow
        workflow = init_keprep_wf()
        workflow.write_graph(graph2use="colored", format="png", simple_form=True)
        workflow.run()

    # function to avoid rerunning if force is not set
    def _check_output_directory(self):
        """
        Check if the output directory already exists
        """
        if not self.inputs.force:
            self.logger.info(
                f"Attempting to locate outputs from previous run in {self.inputs.output_directory}"
            )
            result = self._list_outputs()
            if all(Path(value).exists() for value in result.values()):
                self.logger.info(
                    f"Outputs already exist in {self.inputs.output_directory}. If you want to run the procedure again, set force=True."
                )
                return

    def _locate_fs_license_file(self):
        """
        Locate the FreeSurfer license file
        """
        if not isdefined(self.inputs.fs_license_file):
            fs_home = os.getenv("FREESURFER_HOME")
            if fs_home is None:
                raise ValueError(
                    "FREESURFER_HOME environment variable is not set and fs_license_file is not provided."
                )
            fs_license_file = Path(fs_home) / "license.txt"
            if not fs_license_file.exists():
                raise ValueError(
                    f"FreeSurfer license file not found at {fs_license_file}"
                )
            self.inputs.fs_license_file = str(Path(fs_home) / "license.txt")

    # def _list_outputs(
    #     self, smriprep_outputs: dict = SMRIPREP_OUTPUTS
    # ) -> Dict[str, str]:
    #     """
    #     List the outputs of the SmriprepProcedure
    #     """
    #     outputs_level = "session" if len(self.sessions) == 1 else "subject"
    #     output_directory = Path(self.inputs.output_directory)
    #     outputs = self._outputs().get()
    #     outputs["output_directory"] = str(output_directory)
    #     for (
    #         output_source,
    #         output_formats,
    #     ) in smriprep_outputs.items():
    #         search_destination = output_directory / output_source
    #         for output, desc in output_formats.items():
    #             key = output if output_source != "freesurfer" else f"fs_{output}"
    #             template = desc.get(outputs_level) if isinstance(desc, dict) else desc
    #             if outputs_level == "session":
    #                 value = template.format(
    #                     subject=self.inputs.participant_label,
    #                     session=self.sessions[0],
    #                 )
    #             else:
    #                 value = template.format(subject=self.inputs.participant_label)
    #             outputs[key] = str(search_destination / value)
    #     if hasattr(self, "log_file_path"):
    #         outputs["log_file"] = str(self.log_file_path)
    #     return outputs

    @property
    def sessions(self):
        """
        Get the sessions
        """
        return [
            session.name.split("-")[-1]
            for session in Path(self.inputs.input_directory).glob("ses-*")
            if session.is_dir()
        ]

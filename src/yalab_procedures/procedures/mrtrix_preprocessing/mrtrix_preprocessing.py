from pathlib import Path

from nipype.interfaces.base import CommandLine, Directory, isdefined, traits

from yalab_procedures.procedures.base.procedure import (
    Procedure,
    ProcedureInputSpec,
    ProcedureOutputSpec,
)
from yalab_procedures.procedures.mrtrix_preprocessing.workflows.mrtrix_preprocessing_wf import (
    init_mrtrix_preprocessing_wf,
)


class MrtrixPreprocessingInputSpec(ProcedureInputSpec):
    """
    Input specification for the MrtrixPreprocessingProcedure
    """

    input_directory = Directory(
        exists=True,
        mandatory=True,
        argstr="-data_path %s",
        desc="BIDS-appropriate input directory.",
    )
    subject_id = traits.Str(mandatory=False, desc="Subject ID")
    session_id = traits.Str(mandatory=False, desc="Session ID")
    comis_cortical_exec = traits.Str(
        exists=True,
        mandatory=True,
        desc="Path to the Comis cortical executable.",
    )
    config_file = traits.File(
        exists=True,
        mandatory=False,
        desc="Configuration file",
    )
    output_directory = Directory(
        exists=False,
        mandatory=True,
        desc="Output directory",
    )
    work_directory = Directory(
        exists=False,
        mandatory=True,
        desc="Working directory",
    )


class MrtrixPreprocessingOutputSpec(ProcedureOutputSpec):
    """
    Output specification for the MrtrixPreprocessingProcedure
    """

    output_directory = Directory(desc="Output directory")


class MrtrixPreprocessingProcedure(Procedure, CommandLine):
    """
    Procedure to preprocess DWI data using MRtrix3
    """

    _cmd = "comis_cortical"
    input_spec = MrtrixPreprocessingInputSpec
    output_spec = MrtrixPreprocessingOutputSpec

    def __init__(self, **inputs: dict):
        super().__init__(**inputs)

    def set_missing_inputs(self):
        """
        Set missing inputs for the MRtrix preprocessing procedure
        """
        self.inputs.subject_id = (
            self.infer_subject_id()
            if not isdefined(self.inputs.subject_id)
            else self.inputs.subject_id
        )
        self.inputs.session_id = (
            self.infer_session_id()
            if not isdefined(self.inputs.session_id)
            else self.inputs.session_id
        )

    def run_procedure(self, **kwargs):
        """
        Run the MRtrix preprocessing procedure
        """
        self.set_missing_inputs()
        wf = self.initiate_workflow()
        return wf

    def initiate_workflow(self):
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

    def _gen_wf_name(self):
        return f"mrtrix_preprocessing_sub-{self.inputs.subject_id}_ses-{self.inputs.session_id}"

    def infer_session_id(self):
        return Path(self.inputs.input_directory).parts[-1].split("-")[-1]

    def infer_subject_id(self):
        return Path(self.inputs.input_directory).parts[-2].split("-")[-1]

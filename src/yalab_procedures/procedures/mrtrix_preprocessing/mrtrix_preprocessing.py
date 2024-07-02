from nipype import Workflow
from nipype.interfaces.base import Directory, isdefined, traits

from yalab_procedures.procedures.base.procedure import (
    Procedure,
    ProcedureInputSpec,
    ProcedureOutputSpec,
)


class MrtrixPreprocessingInputSpec(ProcedureInputSpec):
    """
    Input specification for the MrtrixPreprocessingProcedure
    """

    input_directory = Directory(
        exists=True,
        mandatory=True,
        desc="BIDS-appropriate input directory.",
    )
    subject_id = traits.Str(mandatory=True, desc="Subject ID")
    session_id = traits.Str(mandatory=True, desc="Session ID")
    minvol = traits.Int(
        259209,
        usedefault=True,
        desc="""Number of voxels for the brains after rescaling.
        The rescaling will be done such that the brain masks of each subject will be as close as possible to this number.
        If not used, the rescaling stepp will be skipped.""",
    )
    stepscale = traits.Float(
        0.5,
        usedefault=True,
        desc="""Step size for the tracking algorithm.""",
    )
    lenscale = traits.List(
        traits.Float,
        usedefault=True,
        desc="""Minimum and maximum tract length.""",
    )
    angle = traits.Int(
        45,
        usedefault=True,
        desc="""Minimum curvature angle for the tractography.""",
    )
    ntracts = traits.Int(
        100000,
        usedefault=True,
        desc="""Number of tracts to generate **after filtering with SIFT**.""",
    )
    nthreads = traits.Int(
        1,
        usedefault=True,
        desc="""Number of threads to use.""",
    )
    overwrite = traits.Bool(
        False,
        usedefault=True,
        desc="""Overwrite existing files.""",
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


class MrtrixPreprocessingProcedure(Procedure):
    """
    Procedure to preprocess DWI data using MRtrix3
    """

    input_spec = MrtrixPreprocessingInputSpec
    output_spec = MrtrixPreprocessingOutputSpec

    def initiate_workflow(self):
        wf = Workflow(name=self._gen_wf_name())
        if isdefined(self.inputs.work_directory):
            wf.base_dir = self.inputs.work_directory
        return wf

    def _gen_wf_name(self):
        return f"mrtrix_preprocessing_sub-{self.inputs.subject_id}_ses-{self.inputs.session_id}"

from nipype.interfaces.base import Directory, traits

from yalab_procedures.procedures.base.procedure import (
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
        desc="BIDS-appropriate input directory containing DWI files",
    )
    subject_id = traits.Str(mandatory=False, desc="Subject ID")
    session_id = traits.Str(mandatory=False, desc="Session ID")
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


class MrtrixPreprocessingOutputSpec(ProcedureOutputSpec):
    """
    Output specification for the MrtrixPreprocessingProcedure
    """

    output_directory = Directory(desc="Output directory")

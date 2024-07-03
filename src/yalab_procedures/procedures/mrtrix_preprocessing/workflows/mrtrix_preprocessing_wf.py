import nipype.pipeline.engine as pe

from yalab_procedures.procedures.mrtrix_preprocessing.workflows.prepare_inputs.prepare_inputs import (
    init_prepare_inputs_wf,
)


def init_mrtrix_preprocessing_wf(name: str) -> pe.Workflow:
    """
    Initialize the MRtrix preprocessing workflow.

    Parameters
    ----------
    name : str
        The name of the workflow

    Returns
    -------
    wf : nipype Workflow
        The MRtrix preprocessing workflow
    """
    wf = pe.Workflow(name=name)
    prepare_inputs_wf = init_prepare_inputs_wf()
    wf.add_nodes([prepare_inputs_wf])
    return wf

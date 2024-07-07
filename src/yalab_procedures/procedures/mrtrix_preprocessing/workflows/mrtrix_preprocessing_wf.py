from pathlib import Path
import nipype.pipeline.engine as pe
from nipype.interfaces.utility import Function, IdentityInterface

from yalab_procedures.procedures.mrtrix_preprocessing.workflows.prepare_inputs.prepare_inputs import (
    init_prepare_inputs_wf,
)


def get_files_from_config(config_file: str, keys: list = ["datain", "index"]):
    """
    Get the files from the configuration file.

    Parameters
    ----------
    config_file : str
        The configuration file
    keys : list
        The keys to extract from the configuration file

    Returns
    -------
    files : list
        The files extracted from the configuration file
    """
    import json
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"Reading configuration file: {config_file}")

    result = {}

    with open(config_file, "r") as f:
        config = json.load(f)
    config = {key.lower(): value for key, value in config.items()}
    for key in keys:
        value = config.get(key, None)
        if value is not None:
            result[key] = value
            logger.info(f"Key {key} found in configuration file")
        else:
            msg = f"Key {key} not found in configuration file"
            logger.error(msg)
            raise ValueError(msg)

    return result.get("datain"), result.get("index")


def run_comis_cortical(
    comis_cortical_exec: str,
    input_directory: str,
    subject_id: str,
    session_id: str,
):
    """
    Run the comis_cortical command.

    Parameters
    ----------
    comis_cortical_exec : str
        The comis_cortical executable
    input_directory : str
        The input directory
    subject_id : str
        The subject ID
    session_id : str
        The session ID
    output_directory : str
        The output directory
    """
    import logging
    import subprocess

    logger = logging.getLogger(__name__)
    msg = "Running comis_cortical command with the following parameters:"
    msg += f"\ncomis_cortical_exec: {comis_cortical_exec}"
    msg += f"\ninput_directory: {input_directory}"
    msg += f"\nsubject_id: {subject_id}"
    msg += f"\nsession_id: {session_id}"
    logger.info(msg)

    command = f"python3 {comis_cortical_exec} {input_directory} {subject_id}_{session_id} {input_directory}"
    logger.info(f"Running command: {command}")
    result = subprocess.run(
        command,
        shell=True,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.stderr:
        raise ValueError(result.stderr)
    logger.info(result.stdout)
    logger.info("Finished running comis_cortical command")
    return result.stdout


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

    # Create input node
    input_node = pe.Node(
        name="inputnode",
        interface=IdentityInterface(
            fields=[
                "input_directory",
                "subject_id",
                "session_id",
                "config_file",
                "comis_cortical_exec",
                "output_directory",
            ]
        ),
    )

    # Create the get files node
    get_files_node = pe.Node(
        name="get_files_node",
        interface=Function(
            input_names=["config_file"],
            output_names=["datain_file", "index_file"],
            function=get_files_from_config,
        ),
    )

    wf.connect([(input_node, get_files_node, [("config_file", "config_file")])])

    # Create the prepare inputs workflow
    prepare_inputs_wf = init_prepare_inputs_wf()
    wf.connect(
        [
            (
                input_node,
                prepare_inputs_wf,
                [
                    ("input_directory", "inputnode.input_directory"),
                    ("subject_id", "inputnode.subject_id"),
                    ("session_id", "inputnode.session_id"),
                    ("config_file", "inputnode.config_file"),
                    ("output_directory", "inputnode.output_directory"),
                ],
            ),
            (
                get_files_node,
                prepare_inputs_wf,
                [
                    ("datain_file", "inputnode.datain_file"),
                    ("index_file", "inputnode.index_file"),
                ],
            ),
        ]
    )
    return wf


def init_comis_cortical_wf(mrtrix_preprocessing_wf: pe.Workflow) -> pe.Workflow:
    """
    Initialize the Comis cortical workflow.

    Parameters
    ----------
    mrtrix_preprocessing_wf : nipype Workflow
        The MRtrix preprocessing workflow

    Returns
    -------
    wf : nipype Workflow
        The Comis cortical workflow
    """
    wf = pe.Workflow(name="comis_cortical_wf")
    wf.base_dir = str(
        Path(mrtrix_preprocessing_wf.base_dir) / mrtrix_preprocessing_wf.name
    )
    input_node = pe.Node(
        name="inputnode",
        interface=IdentityInterface(
            fields=["comis_cortical_exec", "subject_id", "session_id", "input_direct"]
        ),
    )
    # Create the run comis cortical node
    run_comis_cortical_node = pe.Node(
        name="run_comis_cortical_node",
        interface=Function(
            input_names=[
                "comis_cortical_exec",
                "input_directory",
                "subject_id",
                "session_id",
            ],
            function=run_comis_cortical,
        ),
    )
    wf.connect(
        [
            (
                mrtrix_preprocessing_wf,
                input_node,
                [
                    ("inputnode.comis_cortical_exec", "comis_cortical_exec"),
                    ("inputnode.subject_id", "subject_id"),
                    ("inputnode.session_id", "session_id"),
                    (
                        "prepare_inputs_wf.outputnode.mrtrix_output_directory",
                        "input_directory",
                    ),
                ],
            ),
            (
                input_node,
                run_comis_cortical_node,
                [
                    ("comis_cortical_exec", "comis_cortical_exec"),
                    ("subject_id", "subject_id"),
                    ("session_id", "session_id"),
                    ("input_directory", "input_directory"),
                ],
            ),
        ]
    )
    return wf
    # wf.connect(
    #     [
    #         (
    #             input_node,
    #             run_comis_cortical_node,
    #             [
    #                 ("comis_cortical_exec", "comis_cortical_exec"),
    #                 ("subject_id", "subject_id"),
    #                 ("session_id", "session_id"),
    #             ],
    #         ),
    #         (
    #             prepare_inputs_wf,
    #             run_comis_cortical_node,
    #             [("outputnode.mrtrix_output_directory", "input_directory")],
    #         ),
    #     ]
    # )
    # return wf

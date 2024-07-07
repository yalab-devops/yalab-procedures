from pathlib import Path

import nipype.pipeline.engine as pe
from nipype.interfaces.utility import Function, IdentityInterface, Merge, Split

from yalab_procedures.interfaces.data_grabber.data_grabber import YALabBidsQuery
from yalab_procedures.procedures.mrtrix_preprocessing.workflows.prepare_inputs.bids_to_input import (
    BIDS_TO_INPUT_MAPPING,
)

TEMPLATES_PATH = Path(__file__).parent / "templates"


def setup_output_directory(output_directory: str, subject_id: str, session_id: str):
    """
    Setup the output directory.
    This function creates the output directory and subdirectories for the MRtrix preprocessing pipeline.

    Parameters
    ----------
    output_directory : str
        The output directory
    subject_id : str
        The subject ID
    session_id : str
        The session ID

    Returns
    -------
    raw_data_output_directory : str
        The raw data output directory (output_directory/subject_id/session_id/raw_data)
    config_files_output_directory : str
        The config files output directory (output_directory/subject_id/session_id/config_files)
    """
    import logging
    from pathlib import Path

    logger = logging.getLogger(__name__)
    MRTRIX_SUBDIRECTORIES = ["config_files", "raw_data"]
    logger.info(
        f"Setting up output directory: {output_directory} with subject ID: {subject_id} and session ID: {session_id}"
    )
    result = {}
    output_directory_path = Path(output_directory)
    output_directory_path = Path(
        output_directory_path / subject_id / session_id
    )  # Create the output directory
    for subdirectory in MRTRIX_SUBDIRECTORIES:
        subdir_path = output_directory_path / subdirectory
        subdir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created subdirectory: {subdir_path}")
        result[subdirectory] = str(subdir_path)

    return output_directory_path, result.get("raw_data"), result.get("config_files")


def copy_file_to_output_directory(in_file: str, output_directory: str, out_name: str):
    """
    Copy a file to the output directory.

    Parameters
    ----------
    in_file : str
        The input file
    output_directory : str
        The output directory
    out_name : str
        The output name

    Returns
    -------
    out_file : str
        The output file
    """
    import logging
    from pathlib import Path
    from shutil import copyfile

    logger = logging.getLogger(__name__)
    logger.info(
        f"Copying file: {in_file} to output directory: {output_directory} as {out_name}"
    )

    in_file_path = Path(in_file)
    output_directory_path = Path(output_directory)
    out_file = output_directory_path / out_name

    copyfile(in_file_path, out_file)

    return out_file


def rename_config_file(in_file: str, subject_id: str, session_id: str):
    """
    Rename the config file to include the subject and session ID.

    Parameters
    ----------
    in_file : str
        The input file
    subject_id : str
        The subject ID
    session_id : str
        The session ID
    """
    import logging
    from pathlib import Path

    logger = logging.getLogger(__name__)

    in_file_path = Path(in_file)
    out_file = in_file_path.parent / f"{subject_id}_{session_id}.json"
    in_file_path.rename(out_file)
    logger.info(
        f"Renaming config file: {in_file} to {out_file} with subject ID: {subject_id} and session ID: {session_id}"
    )

    return out_file


def get_bids_directory(input_directory: str):
    """
    Get the BIDS directory from the input directory.

    Parameters
    ----------
    input_directory : str
        The input directory

    Returns
    -------
    bids_directory : str
        The BIDS directory
    """
    import logging
    from pathlib import Path

    logger = logging.getLogger(__name__)

    logger.info(f"Getting BIDS directory from input directory: {input_directory}")
    input_directory_path = Path(input_directory)
    bids_dir = str(input_directory_path.parent.parent)
    logger.info(f"Found BIDS directory: {bids_dir}")

    return bids_dir


def init_prepare_inputs_wf():
    """
    Prepare inputs workflow.
    This workflow prepares the inputs for the MRtrix preprocessing pipeline.

    Returns
    -------
    prepare_inputs_wf : nipype Workflow
        The prepare inputs workflow
    """

    # Create the workflow
    prepare_inputs_wf = pe.Workflow(name="prepare_inputs_wf")

    # Create the input node
    input_node = pe.Node(
        IdentityInterface(
            fields=[
                "subject_id",
                "session_id",
                "input_directory",
                "output_directory",
                "datain_file",
                "index_file",
                "config_file",
            ]
        ),
        name="inputnode",
    )

    # Create the output node
    output_node = pe.Node(
        IdentityInterface(
            fields=[
                "mrtrix_output_directory",
                "raw_data_output_directory",
                "config_files_output_directory",
                "datain_file",
                "index_file",
                "config_file",
            ]
            + [val.split(".")[0] for val in BIDS_TO_INPUT_MAPPING.values()],
        ),
        name="outputnode",
    )

    # Create the setup output directory node
    setup_output_directory_node = pe.Node(
        Function(
            function=setup_output_directory,
            input_names=[
                "output_directory",
                "subject_id",
                "session_id",
                "index_file",
                "datain_file",
                "config_json",
            ],
            output_names=[
                "mrtrix_output_directory",
                "raw_data_output_directory",
                "config_files_output_directory",
            ],
        ),
        name="setup_output_directory_node",
        run_without_submitting=True,
    )

    # Connect input_node to setup_output_directory_node
    prepare_inputs_wf.connect(
        [
            (
                input_node,
                setup_output_directory_node,
                [
                    ("output_directory", "output_directory"),
                    ("subject_id", "subject_id"),
                    ("session_id", "session_id"),
                ],
            ),
        ]
    )

    # Create the get bids directory node
    get_bids_directory_node = pe.Node(
        Function(
            function=get_bids_directory,
            input_names=["input_directory"],
            output_names=["bids_directory"],
        ),
        name="get_bids_directory_node",
        run_without_submitting=True,
    )

    # Connect input_node to get_bids_directory_node
    prepare_inputs_wf.connect(
        [
            (
                input_node,
                get_bids_directory_node,
                [("input_directory", "input_directory")],
            ),
        ]
    )
    # Create the bids query node
    bids_query_node = pe.Node(
        YALabBidsQuery(raise_on_empty=False),
        name="bids_query_node",
        run_without_submitting=True,
    )
    prepare_inputs_wf.connect(
        [(get_bids_directory_node, bids_query_node, [("bids_directory", "base_dir")])]
    )
    prepare_inputs_wf.connect(
        [
            (
                input_node,
                bids_query_node,
                [("subject_id", "subject"), ("session_id", "session")],
            ),
        ]
    )

    # Create the copy raw data node - a map node that copies the raw data to the output directory
    copy_raw_data_node = pe.MapNode(
        Function(
            function=copy_file_to_output_directory,
            input_names=["in_file", "output_directory", "out_name"],
            output_names=["out_file"],
        ),
        name="copy_raw_data_node",
        iterfield=["in_file", "out_name"],
        run_without_submitting=True,
    )

    # Create a node to copy the config file to the configureation directory
    copy_config_node = pe.Node(
        Function(
            function=copy_file_to_output_directory,
            input_names=["in_file", "output_directory", "out_name"],
            output_names=["out_file"],
        ),
        name="copy_config_node",
        run_without_submitting=True,
    )
    copy_config_node.inputs.out_name = "config.json"
    prepare_inputs_wf.connect(
        [
            (input_node, copy_config_node, [("config_file", "in_file")]),
            (
                setup_output_directory_node,
                copy_config_node,
                [("config_files_output_directory", "output_directory")],
            ),
        ]
    )
    rename_config_node = pe.Node(
        Function(
            function=rename_config_file,
            input_names=["in_file", "subject_id", "session_id"],
            output_names=["out_file"],
        ),
        name="rename_config_node",
        run_without_submitting=True,
    )
    prepare_inputs_wf.connect(
        [
            (
                input_node,
                rename_config_node,
                [("subject_id", "subject_id"), ("session_id", "session_id")],
            ),
            (copy_config_node, rename_config_node, [("out_file", "in_file")]),
            (rename_config_node, output_node, [("out_file", "config_file")]),
        ]
    )

    # Connecting setup output directory node

    prepare_inputs_wf.connect(
        setup_output_directory_node,
        "raw_data_output_directory",
        copy_raw_data_node,
        "output_directory",
    )
    prepare_inputs_wf.connect(
        [
            (
                setup_output_directory_node,
                output_node,
                [
                    ("mrtrix_output_directory", "mrtrix_output_directory"),
                    ("config_files_output_directory", "config_files_output_directory"),
                    ("raw_data_output_directory", "raw_data_output_directory"),
                ],
            ),
        ]
    )

    n_splits = len(BIDS_TO_INPUT_MAPPING) + 2
    # Ensure listify nodes are used to create list inputs for the MapNode iterfields
    listify_bids_query_outputs_node = pe.Node(
        Merge(n_splits),
        name="listify_bids_query_outputs_node",
        run_without_submitting=True,
    )

    listify_copy_data_inputs_node = pe.Node(
        Merge(n_splits),
        name="listify_copy_data_inputs_node",
        run_without_submitting=True,
    )

    split_to_outputs_node = pe.Node(
        Split(splits=[1] * n_splits),
        name="split_to_outputs_node",
        run_without_submitting=True,
    )
    # add index and datain to the listify_copy_data_inputs_node
    for j, fname in enumerate(["datain_file.txt", "index_file.txt"]):
        out_fname = fname.replace("_file", "")
        # listify_bids_query_outputs_node.inputs.trait_set(
        #     **{f"in{j+1}": [str(TEMPLATES_PATH / fname)]}
        # )
        listify_copy_data_inputs_node.inputs.trait_set(**{f"in{j+1}": [out_fname]})
        prepare_inputs_wf.connect(
            [
                (
                    input_node,
                    listify_bids_query_outputs_node,
                    [(fname.split(".")[0], f"in{j+1}")],
                ),
                (
                    split_to_outputs_node,
                    output_node,
                    [(f"out{j+1}", fname.split(".")[0])],
                ),
            ]
        )
    # Populate listify nodes
    for i, (src, dest) in enumerate(BIDS_TO_INPUT_MAPPING.items()):
        prepare_inputs_wf.connect(
            bids_query_node, src, listify_bids_query_outputs_node, f"in{j+i+2}"
        )
        listify_copy_data_inputs_node.inputs.trait_set(**{f"in{j+i+2}": dest})
        prepare_inputs_wf.connect(
            split_to_outputs_node,
            f"out{j+i+2}",
            output_node,
            dest.split(".")[0],
        )

    # Connect the listify nodes to the copy raw data node
    prepare_inputs_wf.connect(
        listify_bids_query_outputs_node, "out", copy_raw_data_node, "in_file"
    )
    prepare_inputs_wf.connect(
        listify_copy_data_inputs_node, "out", copy_raw_data_node, "out_name"
    )
    prepare_inputs_wf.connect(
        copy_raw_data_node, "out_file", split_to_outputs_node, "inlist"
    )

    return prepare_inputs_wf

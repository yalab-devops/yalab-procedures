# tests/procedures/procedure/test_dicom_to_bids.py

import tempfile
from datetime import datetime
from pathlib import Path
from subprocess import CalledProcessError
from unittest.mock import patch

import pytest

from yalab_procedures.procedures.dicom_to_bids.dicom_to_bids import DicomToBidsProcedure


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def dicom_to_bids_procedure(temp_dir):
    input_dir = temp_dir / "input"
    output_dir = temp_dir / "output"
    logging_dir = temp_dir / "logs"

    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    logging_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "input_directory": str(input_dir),
        "output_directory": str(output_dir),
        "logging_directory": str(logging_dir),
        "logging_level": "DEBUG",
        "subject_id": "test_subject",
        "session_id": "01",
    }
    procedure = DicomToBidsProcedure(**config)
    return procedure


@pytest.fixture
def dicom_to_bids_procedure_no_session(temp_dir):
    today_date = datetime.now().strftime("%Y%m%d")
    now_time = datetime.now().strftime("%H%M%S")
    input_dir = temp_dir / f"TMP_DICOM_{today_date}_{now_time}"
    output_dir = temp_dir / "output"
    logging_dir = temp_dir / "logs"

    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    logging_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "input_directory": str(input_dir),
        "output_directory": str(output_dir),
        "logging_directory": str(logging_dir),
        "logging_level": "DEBUG",
        "subject_id": "test_subject",
    }
    procedure = DicomToBidsProcedure(**config)
    return procedure


def test_initialization(dicom_to_bids_procedure):
    assert Path(dicom_to_bids_procedure.inputs.input_directory).exists()
    assert Path(dicom_to_bids_procedure.inputs.output_directory).exists()
    assert Path(dicom_to_bids_procedure.inputs.logging_directory).exists()
    assert Path(dicom_to_bids_procedure.inputs.heuristic_file).exists()


def test_command_line_construction(dicom_to_bids_procedure):
    expected_command = (
        f"heudiconv --bids "
        f"-c dcm2niix "
        f"-f {dicom_to_bids_procedure.inputs.heuristic_file} "
        f"--files {dicom_to_bids_procedure.inputs.input_directory}/*/*.dcm "
        f"-o {dicom_to_bids_procedure.inputs.output_directory} "
        f"--overwrite "
        f"-ss {dicom_to_bids_procedure.inputs.session_id} "
        f"-s {dicom_to_bids_procedure.inputs.subject_id} "
    ).strip()
    cmd_args = dicom_to_bids_procedure._parse_inputs()
    cmd = [dicom_to_bids_procedure._cmd] + cmd_args
    constructed_command = " ".join(cmd).strip()
    assert (
        constructed_command == expected_command
    ), f"Constructed: {constructed_command}\nExpected: {expected_command}"


def test_infer_session_id(dicom_to_bids_procedure_no_session):
    """
    Test that the session ID is inferred from the input directory name when not provided.

    Parameters
    ----------
    dicom_to_bids_procedure_no_session : DicomToBidsProcedure
        Procedure object with no session ID provided.
    """
    true_session_id = "".join(
        Path(dicom_to_bids_procedure_no_session.inputs.input_directory).name.split("_")[
            2:
        ]
    )
    dicom_to_bids_procedure_no_session.infer_session_id()
    assert dicom_to_bids_procedure_no_session.inputs.session_id == true_session_id


@patch("subprocess.run")
def test_run_procedure(mock_run, dicom_to_bids_procedure):
    mock_run.return_value.returncode = 0
    with pytest.raises(CalledProcessError):
        dicom_to_bids_procedure.run()


@patch("subprocess.run")
def test_logging_setup(mock_run, dicom_to_bids_procedure):
    mock_run.return_value.returncode = 0
    with pytest.raises(CalledProcessError):
        dicom_to_bids_procedure.run()
    log_files = list(
        Path(dicom_to_bids_procedure.inputs.logging_directory).glob("*.log")
    )
    assert len(log_files) == 1
    with open(log_files[0], "r") as log_file:
        log_content = log_file.read()
        assert "Running DicomToBidsProcedure" in log_content


@patch("subprocess.run")
def test_logger_contains_error(mock_run, dicom_to_bids_procedure):
    mock_run.return_value.returncode = 1
    mock_run._cmd = "wrong_command"
    with pytest.raises(CalledProcessError):
        dicom_to_bids_procedure.run()
    log_files = list(
        Path(dicom_to_bids_procedure.inputs.logging_directory).glob("*.log")
    )
    assert len(log_files) == 1

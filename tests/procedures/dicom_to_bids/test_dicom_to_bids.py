# tests/procedures/procedure/test_dicom_to_bids.py

import tempfile
from pathlib import Path
from subprocess import CalledProcessError
from unittest.mock import patch

import pytest

from yalab_procedures.procedures.dicom_to_bids import DicomToBidsProcedure


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def dicom_to_bids_procedure(temp_dir):
    input_dir = temp_dir / "input"
    output_dir = temp_dir / "output"
    logging_dir = temp_dir / "logs"
    heuristic_file = temp_dir / "heuristic.py"

    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    logging_dir.mkdir(parents=True, exist_ok=True)
    heuristic_file.touch()

    config = {
        "input_directory": str(input_dir),
        "output_directory": str(output_dir),
        "logging_directory": str(logging_dir),
        "logging_level": "DEBUG",
        "subject_id": "test_subject",
        "session_id": "01",
        "heuristic_file": str(heuristic_file),
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
        f"heudiconv --files {dicom_to_bids_procedure.inputs.input_directory}/*/*.dcm "
        f"-o {dicom_to_bids_procedure.inputs.output_directory} "
        f"-f {dicom_to_bids_procedure.inputs.heuristic_file} "
        f"-s {dicom_to_bids_procedure.inputs.subject_id} "
        f"-ss {dicom_to_bids_procedure.inputs.session_id} "
        f"-c dcm2niix "
        f"--overwrite "
        f"--bids"
    ).strip()
    cmd_args = dicom_to_bids_procedure._parse_inputs()
    cmd = [dicom_to_bids_procedure._cmd] + cmd_args
    constructed_command = " ".join(cmd).strip()
    assert (
        constructed_command == expected_command
    ), f"Constructed: {constructed_command}\nExpected: {expected_command}"


@patch("subprocess.run")
def test_run_procedure(mock_run, dicom_to_bids_procedure):
    mock_run.return_value.returncode = 0
    try:
        dicom_to_bids_procedure.run()
        mock_run.assert_called_once()
    except CalledProcessError as e:
        pytest.fail(f"run_procedure raised CalledProcessError unexpectedly: {e}")


@patch("subprocess.run")
def test_logging_setup(mock_run, dicom_to_bids_procedure):
    mock_run.return_value.returncode = 0
    dicom_to_bids_procedure.run()
    log_files = list(dicom_to_bids_procedure.inputs.logging_directory.glob("*.log"))
    assert len(log_files) == 1
    with open(log_files[0], "r") as log_file:
        log_content = log_file.read()
        assert "Running DicomToBidsProcedure" in log_content


if __name__ == "__main__":
    pytest.main()

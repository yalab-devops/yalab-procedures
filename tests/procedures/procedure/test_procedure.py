# tests/procedures/procedure/test_procedure.py

import tempfile
from pathlib import Path

import pytest

from tests.procedures.procedure.mock_procedure import MockProcedure
from yalab_procedures.procedures.procedure import Procedure


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_procedure(temp_dir):
    input_dir = temp_dir / "input"
    output_dir = temp_dir / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "input_directory": str(input_dir),
        "output_directory": str(output_dir),
    }
    procedure = MockProcedure(**config)
    return procedure


def test_input_directory_validation(mock_procedure):
    assert Path(mock_procedure.inputs.input_directory).exists()


def test_output_directory_setup(mock_procedure):
    mock_procedure.run()
    assert Path(mock_procedure.inputs.output_directory).exists()


def test_logging_setup(temp_dir):
    input_dir = temp_dir / "input"
    output_dir = temp_dir / "output"
    log_dir = temp_dir / "logs"
    input_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "input_directory": str(input_dir),
        "output_directory": str(output_dir),
        "logging_directory": str(log_dir),
        "logging_level": "DEBUG",
    }

    procedure = MockProcedure(**config)
    procedure.run()

    log_files = list(log_dir.glob("*.log"))
    assert len(log_files) == 1
    with open(log_files[0], "r") as log_file:
        log_content = log_file.read()
        assert "Running the mock procedure" in log_content


def test_naive_procedure(temp_dir):
    input_dir = temp_dir / "input"
    output_dir = temp_dir / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "input_directory": str(input_dir),
        "output_directory": str(output_dir),
    }
    procedure = Procedure(**config)
    with pytest.raises(NotImplementedError):
        procedure.run()

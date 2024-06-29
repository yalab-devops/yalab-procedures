# tests/procedures/procedure/test_procedure.py

import json
import tempfile
from pathlib import Path

import pytest

from tests.procedures.procedure.mock_procedure import MockProcedure


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
    procedure = MockProcedure(config=config)
    procedure.validate_and_set_inputs(procedure.load_config(config))
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

    procedure = MockProcedure(config=config)
    procedure.validate_and_set_inputs(procedure.load_config(config))
    procedure.run()

    log_files = list(log_dir.glob("*.log"))
    assert len(log_files) == 1
    with open(log_files[0], "r") as log_file:
        log_content = log_file.read()
        assert "Running the mock procedure" in log_content


def test_load_config_dict(temp_dir):
    input_dir = temp_dir / "input"
    output_dir = temp_dir / "output"
    input_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "input_directory": str(input_dir),
        "output_directory": str(output_dir),
    }
    procedure = MockProcedure(config=config)
    procedure.validate_and_set_inputs(procedure.load_config(config))
    assert procedure.inputs.input_directory == str(input_dir)
    assert procedure.inputs.output_directory == str(output_dir)


def test_load_config_file(temp_dir):
    input_dir = temp_dir / "input"
    output_dir = temp_dir / "output"
    config_file = temp_dir / "config.json"
    config_data = {
        "input_directory": str(input_dir),
        "output_directory": str(output_dir),
    }
    input_dir.mkdir(parents=True, exist_ok=True)

    with open(config_file, "w") as f:
        json.dump(config_data, f)

    procedure = MockProcedure(config=str(config_file))
    config = procedure.load_config(str(config_file))
    procedure.validate_and_set_inputs(config)
    assert procedure.inputs.input_directory == str(input_dir)
    assert procedure.inputs.output_directory == str(output_dir)

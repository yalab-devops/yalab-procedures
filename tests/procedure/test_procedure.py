# tests/procedure/test_procedure.py
import json
import tempfile
from pathlib import Path

import pytest

from tests.procedure.mock_procedure import MockProcedure
from yalab_procedures.procedure.procedure import Procedure


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_procedure(temp_dir):
    input_dir = temp_dir / "input"
    output_dir = temp_dir / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    return MockProcedure(input_directory=input_dir, output_directory=output_dir)


def base_procedure_raises_error():
    with pytest.raises(NotImplementedError):
        procedure = Procedure(input_directory="input", output_directory="output")
        procedure.run()


def test_missing_input_directory_raises_error():
    with pytest.raises(FileNotFoundError):
        _ = MockProcedure(input_directory="input", output_directory="output")


def test_input_directory_validation(mock_procedure):
    assert mock_procedure.input_directory.exists()


def test_output_directory_setup(mock_procedure):
    assert mock_procedure.output_directory.exists()


def test_logging_setup(mock_procedure):
    assert mock_procedure.logger.name == "MockProcedure"


def test_logging_file_creation(temp_dir):
    input_dir = temp_dir / "input"
    output_dir = temp_dir / "output"
    log_dir = temp_dir / "logs"
    input_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    procedure = MockProcedure(
        input_directory=input_dir,
        output_directory=output_dir,
        logging_destination=log_dir,
    )
    procedure.log("Test log message.")

    log_files = list(log_dir.glob("*.log"))
    assert len(log_files) == 1
    with open(log_files[0], "r") as log_file:
        log_content = log_file.read()
        assert "Test log message." in log_content


def test_load_config_dict(mock_procedure):
    config = {"key": "value"}
    procedure = MockProcedure(
        input_directory=mock_procedure.input_directory,
        output_directory=mock_procedure.output_directory,
        config=config,
    )
    assert procedure.config == config


def test_load_config_file(temp_dir):
    input_dir = temp_dir / "input"
    output_dir = temp_dir / "output"
    config_file = temp_dir / "config.json"
    config_data = {"key": "value"}
    input_dir.mkdir(parents=True, exist_ok=True)

    with open(config_file, "w") as f:
        json.dump(config_data, f)

    procedure = MockProcedure(
        input_directory=input_dir, output_directory=output_dir, config=config_file
    )
    assert procedure.config == config_data


def test_config_json_decode_returns_empty_dict(temp_dir):
    input_dir = temp_dir / "input"
    output_dir = temp_dir / "output"
    config_file = temp_dir / "config.json"
    input_dir.mkdir(parents=True, exist_ok=True)

    with open(config_file, "w") as f:
        f.write("invalid json")

    procedure = MockProcedure(
        input_directory=input_dir, output_directory=output_dir, config=config_file
    )
    assert procedure.config == {}

import tempfile
from pathlib import Path

import pytest

from yalab_procedures.procedures.neuroflow import NeuroflowProcedure


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def neuroflow_procedure(temp_dir):
    input_dir = temp_dir / "input"
    output_dir = temp_dir / "output"
    google_credentials = temp_dir / "google_credentials.json"

    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    google_credentials.write_text("")

    config = {
        "input_directory": str(input_dir),
        "output_directory": str(output_dir),
        "google_credentials": str(google_credentials),
        "atlases": ["fan2016", "huang2022"],
    }
    procedure = NeuroflowProcedure(**config)
    return procedure


def test_neuroflow_procedure_init(neuroflow_procedure):
    assert Path(neuroflow_procedure.inputs.input_directory).exists()
    assert Path(neuroflow_procedure.inputs.output_directory).exists()
    assert Path(neuroflow_procedure.inputs.google_credentials).exists()
    assert neuroflow_procedure.inputs.atlases == ["fan2016", "huang2022"]
    assert neuroflow_procedure.inputs.force == False  # noqa: E712
    assert neuroflow_procedure.inputs.max_bval == 1000
    assert neuroflow_procedure.inputs.use_smriprep == True  # noqa: E712


def test_command_line_construction(neuroflow_procedure):
    cmd = neuroflow_procedure.cmdline
    print(cmd)
    expected_cmd = (
        f"neuroflow process "
        f"{neuroflow_procedure.inputs.input_directory} "
        f"{neuroflow_procedure.inputs.output_directory} "
        f"{neuroflow_procedure.inputs.google_credentials} "
        f"--atlases fan2016,huang2022 "
        f"--crop_to_gm --max_bval 1000 --use_smriprep"
    ).strip()
    assert cmd == expected_cmd

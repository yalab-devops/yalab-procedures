import tempfile
from pathlib import Path

import pytest

from yalab_procedures.procedures.keprep.keprep import KePrepProcedure


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdirname:
        yield Path(tmpdirname)


@pytest.fixture
def keprep_procedure(temp_dir):
    input_dir = temp_dir / "input"
    output_dir = temp_dir / "output"
    logging_dir = temp_dir / "logs"
    work_dir = temp_dir / "work"
    participant_label = "test"

    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    logging_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "input_directory": str(input_dir),
        "output_directory": str(output_dir),
        "logging_directory": str(logging_dir),
        "work_directory": str(work_dir),
        "participant_label": [participant_label],
    }
    procedure = KePrepProcedure(**config)
    return procedure


def test_keprep_procedure_init(keprep_procedure):
    assert Path(keprep_procedure.inputs.input_directory).exists()
    assert Path(keprep_procedure.inputs.output_directory).exists()
    assert Path(keprep_procedure.inputs.logging_directory).exists()
    assert Path(keprep_procedure.inputs.work_directory).exists
    assert keprep_procedure.inputs.participant_label == ["test"]
    assert keprep_procedure.inputs.force == False  # noqa: E712
    assert keprep_procedure.inputs.omp_nthreads == 1


def test_failed_execution(keprep_procedure):
    with pytest.raises(ValueError):
        keprep_procedure.run()


def test_default_config(keprep_procedure):
    configuration_dict = keprep_procedure._setup_config_toml()
    assert configuration_dict["participant_label"] == ["test"]
    assert configuration_dict["force"] == False  # noqa: E712
    assert configuration_dict["omp_nthreads"] == 1
    assert configuration_dict["output_dir"] == str(
        keprep_procedure.inputs.output_directory
    )
    assert configuration_dict["reset_database"] == True  # noqa: E712
    assert configuration_dict["hires"] == True  # noqa: E712
    assert configuration_dict["do_reconall"] == True  # noqa: E712
    assert configuration_dict["dwi2t1w_dof"] == 6

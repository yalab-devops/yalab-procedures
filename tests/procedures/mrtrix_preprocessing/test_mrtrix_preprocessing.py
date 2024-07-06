from unittest.mock import patch

import pytest

from yalab_procedures.procedures.mrtrix_preprocessing.mrtrix_preprocessing import (
    MrtrixPreprocessingProcedure,
)


@pytest.fixture
def procedure():
    # Mocking directly in the fixture to ensure all tests get the benefit
    with patch("pathlib.Path.exists", return_value=True):
        with patch("os.path.exists", return_value=True):
            proc = MrtrixPreprocessingProcedure(
                input_directory="/fake/dir",
                subject_id="123",
                session_id="456",
                comis_cortical_exec="/fake/path/comis_cortical",
                config_file="/fake/path/config.json",
                output_directory="/fake/output",
                work_directory="/fake/work",
            )
    return proc


def test_download_comis_cortical_exec(procedure):
    with patch("git.Git") as mock_git:
        mock_git.clone.return_value = None  # Simulate cloning
        result = procedure._download_comis_cortical_exec()
        assert "comis_cortical" in result
        mock_git.assert_called_once()


def test_validate_comis_cortical_exec_provided(procedure):
    procedure.validate_comis_cortical_exec()
    assert procedure.inputs.comis_cortical_exec == "/fake/path/comis_cortical"


def test_validate_comis_cortical_exec_downloaded(procedure):
    with patch(
        "MrtrixPreprocessingProcedure._download_comis_cortical_exec",
        return_value="/downloaded/path/comis_cortical",
    ):
        procedure.validate_comis_cortical_exec()
        assert procedure.inputs.comis_cortical_exec == "/downloaded/path/comis_cortical"


def test_infer_subject_id(procedure):
    assert procedure.infer_subject_id() == "123"


def test_infer_session_id(procedure):
    assert procedure.infer_session_id() == "456"

import os
import tempfile
from pathlib import Path

import pytest

from yalab_procedures.procedures.axsi import AxsiProcedure


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def axsi_procedure(temp_dir):
    input_dir = temp_dir / "input"
    output_dir = temp_dir / "output"
    logging_dir = temp_dir / "logs"

    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    logging_dir.mkdir(parents=True, exist_ok=True)

    data = input_dir / 'data.nii.gz'
    mask = input_dir / 'mask.nii.gz'
    bval = input_dir / 'bval.txt'
    bvec = input_dir / 'bvec.txt'
    data.touch()
    mask.touch()
    bval.touch()
    bvec.touch()

    config = {
        "input_directory": str(input_dir),
        "output_directory": str(output_dir),
        "logging_directory": str(logging_dir),
        "run_name": "test-run",
        "data": data,
        "mask": mask,
        "bval": bval,
        "bvec": bvec,
        "linear_lsq_method": "cvxpy",
    }
    procedure = AxsiProcedure(**config)
    return procedure


def test_axsi_procedure_init(axsi_procedure):
    assert Path(axsi_procedure.inputs.input_directory).exists()
    assert Path(axsi_procedure.inputs.output_directory).exists()
    assert axsi_procedure.inputs.linear_lsq_method == "cvxpy"
    assert axsi_procedure.inputs.nonlinear_lsq_method == "R-minpack"  # noqa: E712
    assert axsi_procedure.inputs.gmax == 7.9
    assert axsi_procedure.inputs.debug_mode == False  # noqa: E712


def test_command_line_construction(axsi_procedure):
    cmd = axsi_procedure.cmdline
    print(cmd)
    expected_cmd = (
        f"axsi-main "
        f"--subj-folder {axsi_procedure.inputs.output_directory} "
        f"--run-name {axsi_procedure.inputs.run_name} "
        f"--data {axsi_procedure.inputs.data} "
        f"--mask {axsi_procedure.inputs.mask} "
        f"--bval {axsi_procedure.inputs.bval} "
        f"--bvec {axsi_procedure.inputs.bvec} "
        f"--small-delta {axsi_procedure.inputs.small_delta:.6f} "  # Format to 6 decimal places
        f"--big-delta {axsi_procedure.inputs.big_delta:.6f} "  # Format to 6 decimal places
        f"--gmax {axsi_procedure.inputs.gmax:.6f} "  # Format to 6 decimal places
        f"--gamma-val {axsi_procedure.inputs.gamma_val} "
        f"--num-processes-pred 1 "
        f"--num-threads-pred 1 "
        f"--num-processes-axsi 1 "
        f"--num-threads-axsi 1 "
        f"--nonlinear-lsq-method {axsi_procedure.inputs.nonlinear_lsq_method} "
        f"--linear-lsq-method {axsi_procedure.inputs.linear_lsq_method}"
    ).strip()
    assert cmd == expected_cmd


def test_failed_execution(axsi_procedure):
    with pytest.raises(Exception):
        axsi_procedure.run()


def test_list_outputs(axsi_procedure):
    outputs = axsi_procedure._list_outputs()
    assert outputs["output_directory"] == str(
        os.path.join(axsi_procedure.inputs.output_directory, axsi_procedure.inputs.run_name))

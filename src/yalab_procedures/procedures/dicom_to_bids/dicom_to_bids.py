# src/yalab_procedures/procedures/dicom_to_bids.py

from pathlib import Path
from subprocess import CalledProcessError, run

from nipype.interfaces.base import (
    CommandLine,
    CommandLineInputSpec,
    Directory,
    File,
    isdefined,
    traits,
)

from yalab_procedures.procedures.base.procedure import (
    Procedure,
    ProcedureInputSpec,
    ProcedureOutputSpec,
)

DEFAULT_HEURISTIC = Path(__file__).parent / "templates" / "heuristic.py"


class DicomToBidsInputSpec(ProcedureInputSpec, CommandLineInputSpec):
    subject_id = traits.Str(argstr="-s %s", mandatory=True, desc="Subject ID")
    session_id = traits.Str(argstr="-ss %s", desc="Session ID")
    heuristic_file = File(
        DEFAULT_HEURISTIC,
        exists=True,
        mandatory=False,
        argstr="-f %s",
        desc="Heuristic file",
        usedefault=True,
    )
    input_directory = Directory(
        exists=True,
        mandatory=True,
        argstr="--files %s/*/*.dcm",
        desc="Input directory containing DICOM files",
    )
    output_directory = Directory(
        exists=True,
        mandatory=True,
        argstr="-o %s",
        desc="Directory to store BIDS output",
    )
    converter = traits.Enum(
        "dcm2niix",
        default="dcm2niix",
        usedefault=True,
        argstr="-c %s",
        desc="DICOM converter to use",
    )
    overwrite = traits.Bool(
        True, usedefault=True, argstr="--overwrite", desc="Overwrite existing files"
    )
    bids = traits.Bool(
        True, usedefault=True, argstr="--bids", desc="Organize output in BIDS format"
    )
    infer_session_id = traits.Bool(
        True,
        usedefault=True,
        desc="Infer session ID from DICOM directory name",
    )


class DicomToBidsOutputSpec(ProcedureOutputSpec):
    bids_directory = Directory(desc="Output BIDS directory")


class DicomToBidsProcedure(Procedure, CommandLine):
    _cmd = "heudiconv"
    input_spec = DicomToBidsInputSpec
    output_spec = DicomToBidsOutputSpec

    def __init__(self, **inputs):
        super(DicomToBidsProcedure, self).__init__(**inputs)
        self.infer_session_id()

    def run_procedure(self, **kwargs):
        try:
            self.logger.info("Running DicomToBidsProcedure")
            self.logger.debug(f"Input attributes: {kwargs}")

            # Run the heudiconv command
            self.run_commandline()

            self.logger.info("Finished running DicomToBidsProcedure")
        except CalledProcessError as e:
            self.logger.error(f"Error running DicomToBidsProcedure: {e}")
            raise

    def infer_session_id(self):
        """
        Infer the session ID from the input directory name.
        This is useful for DICOM directories provided by TAU's MRI facility.
        """
        if not isdefined(self.inputs.session_id) and self.inputs.infer_session_id:
            session_id = Path(self.inputs.input_directory).name.split("_")[-2:]
            session_id = "".join(session_id)
            self.inputs.session_id = session_id

    def run_commandline(self):
        # Build the command line arguments
        cmd_args = self._parse_inputs()
        cmd = [self._cmd] + cmd_args
        self.logger.debug(f"Command line: {' '.join(cmd)}")

        # Run the command
        result = run(
            " ".join(cmd), shell=True, check=True, capture_output=True, text=True
        )
        self.logger.info(result.stdout)
        if result.stderr:
            self.logger.error(result.stderr)

    def _list_outputs(self):
        outputs = self._outputs().get()
        outputs["bids_directory"] = str(self.inputs.output_directory)
        return outputs


if __name__ == "__main__":
    custom_procedure = DicomToBidsProcedure(
        input_directory="/media/groot/Minerva/ya_shared/YA_lab_Yaniv_General_20240609_1801",
        output_directory="/media/groot/Minerva/ya_shared/output_tmp/",
        logging_directory="/media/groot/Minerva/ya_shared/output_tmp/",
        logging_level="DEBUG",
        subject_id="003006",
        session_id="01",  # if applicable
        heuristic_file="/home/groot/Projects/yalab-dev/yalab_procedures/src/yalab_procedures/procedures/dicom_to_bids/templates/heuristic.py",
    )
    custom_procedure.run()

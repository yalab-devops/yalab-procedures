import os
import os.path as op
from pathlib import Path
from typing import Any

import keprep
from keprep import config, data
from keprep.config import init_spaces
from keprep.data.quality_assurance.reports import build_boilerplate, run_reports
from keprep.workflows.base.workflow import init_keprep_wf
from nipype.interfaces.base import Directory, File, isdefined, traits
from niworkflows.engine.workflows import LiterateWorkflow as Workflow

from yalab_procedures.procedures.base.procedure import (
    Procedure,
    ProcedureInputSpec,
    ProcedureOutputSpec,
)
from yalab_procedures.procedures.keprep_procedure.templates.inputs import INPUTS_MAPPING


class KePrepInputSpec(ProcedureInputSpec):
    """
    Input specification for the KePrepProcedure
    """

    # Execution configuration
    input_directory = Directory(
        exists=True,
        mandatory=True,
        desc="Input directory containing raw data in BIDS format",
    )
    output_directory = Directory(
        exists=False,
        mandatory=True,
        desc="Path to store outputs of KePrep.",
    )
    anat_derivatives = Directory(
        exists=False,
        mandatory=False,
        desc="Directory to store anatomical derivatives",
    )
    bids_database_dir = Directory(
        exists=False,
        mandatory=False,
        desc="Directory containing SQLite database indices for the input BIDS dataset.",
    )
    bids_filters = traits.File(
        exists=True,
        argstr="-v %s:/bids_filters.json",
        desc="BIDS filter file",
    )
    reset_database = traits.Bool(
        True,
        usedefault=True,
        desc="Whether to reset the database",
    )
    fs_license_file = File(
        exists=True,
        mandatory=False,
        desc="Path to FreeSurfer license file",
    )
    fs_subjects_dir = Directory(
        exists=False,
        mandatory=False,
        desc="Path to FreeSurfer subjects directory",
    )
    participant_label = traits.List(
        traits.Str,
        argstr="--participant_label %s",
        desc="Participant label",
        sep=",",
    )
    work_directory = Directory(
        exists=False,
        mandatory=True,
        argstr="-v %s:/work",
        desc="Path to work directory",
    )
    output_spaces = traits.List(
        traits.Str,
        argstr="--output-spaces %s",
        desc="Output spaces",
        sep=",",
    )
    # Workflow configuration
    anat_only = traits.Bool(
        False,
        usedefault=True,
        desc="Whether to run anatomical processing only",
    )
    dwi2t1w_dof = traits.Int(
        6,
        usedefault=True,
        desc="Degrees of freedom for the DWI-to-T1w registration",
    )
    dwi2t1w_init = traits.Str(
        "header",
        usedefault=True,
        desc="Initialization for the DWI-to-T1w registration",
    )
    do_reconall = traits.Bool(
        True,
        usedefault=True,
        desc="Whether to run FreeSurfer recon-all",
    )
    longitudinal = traits.Bool(
        True,
        argstr="--longitudinal",
        desc="Longitudinal processing. May increase runtime.",
    )
    skull_strip_fixed_seed = traits.Bool(
        False,
        usedefault=True,
        desc="Whether to use a fixed seed for skull stripping",
    )
    skull_strip_template = traits.Str(
        "OASIS30ANTs",
        usedefault=True,
        desc="Template for skull stripping",
    )
    hires = traits.Bool(
        True,
        usedefault=True,
        desc="Whether to run the high-resolution workflow",
    )
    # Nipype configuration
    crashfile_format = traits.Enum(
        "txt",
        "txt.gz",
        "no",
        usedefault=True,
        desc="Crashfile format",
    )
    nprocs = traits.Int(
        os.cpu_count(),
        usedefault=True,
        desc="Number of processes (compute tasks) that can be run in parallel (multiprocessing only).",
    )
    omp_nthreads = traits.Int(
        1,
        usedefault=True,
        desc="Number of CPUs a single process can access for multithreaded execution.",
    )
    stop_on_first_crash = traits.Bool(
        False,
        usedefault=True,
        desc="Whether to stop on first crash",
    )
    write_graph = traits.Bool(
        False, usedefault=True, desc="Whether to write the workflow's graph"
    )
    force = traits.Bool(
        False,
        usedefault=True,
        desc="Whether to force the procedure to run even if the output directory already exists.",
    )


class KePrepOutputSpec(ProcedureOutputSpec):
    """
    Output specification for the KePrepProcedure
    """

    output_directory = Directory(desc="KePrep output directory")


class KePrepProcedure(Procedure):
    """
    Procedure for running Smriprep
    """

    input_spec = KePrepInputSpec
    output_spec = KePrepOutputSpec
    _version = keprep.__version__

    def __init__(self, **inputs: Any):
        super().__init__(**inputs)

    def _setup_config_toml(self):
        """
        Set up the configuration file
        """
        inputs_dict = self.inputs.get()
        configuration_dict = {}
        for key, value in inputs_dict.items():
            if key in INPUTS_MAPPING:
                target_key = INPUTS_MAPPING.get(key)
                if not isdefined(value):
                    default_value = self._get_default_value(key)
                    if isdefined(default_value):
                        configuration_dict[target_key] = default_value
                    else:
                        raise ValueError(f"Value for {key} not provided.")
                else:
                    configuration_dict[target_key] = value
            else:
                if isdefined(value):
                    configuration_dict[key] = value
        return configuration_dict

    def _get_default_value(self, key: str) -> Any:
        """
        Get the default value of an input
        """
        value = getattr(self.inputs, key)
        return value if isdefined(value) else self.inputs.traits().get(key).default

    def run_procedure(self, **kwargs):
        """
        Run the SmriprepProcedure

        Raises
        ------
        CalledProcessError
            If the command fails to run. The error message will be logged.
        """

        self.logger.info("Running KePrepProcedure")
        self.logger.debug(f"Input attributes: {kwargs}")

        # Locate the FreeSurfer license file
        self._locate_fs_license_file()
        # Prepare inputs
        configuration_dict = self._setup_config_toml()
        config.from_dict(configuration_dict)
        init_spaces()
        # Set up directories
        # self._set_up_directories()
        # Run the workflow
        workflow = init_keprep_wf()
        if self.inputs.write_graph:
            workflow.write_graph(graph2use="colored", format="png", simple_form=True)
        workflow.run()
        self._generate_reports(workflow=workflow, configuration_dict=configuration_dict)

    def _generate_reports(self, workflow: Workflow, configuration_dict: dict):
        # Generate reports
        build_boilerplate(config_file=configuration_dict, workflow=workflow)
        bootstrap_file = data.load("quality_assurance/templates/reports-spec.yml")
        run_uuid = config.execution.run_uuid
        for participant_label in self.inputs.participant_label:
            err = run_reports(
                config.execution.keprep_dir,
                participant_label,
                run_uuid,
                bootstrap_file=bootstrap_file,
                out_filename="report.html",
                reportlets_dir=config.execution.keprep_dir,
                errorname=f"report-{run_uuid}-{participant_label}.err",
                subject=participant_label,
            )
            if err:
                self.logger.warn(
                    f"Failed to generate report for subject {participant_label}"
                )

    # function to avoid rerunning if force is not set
    def _check_output_directory(self):
        """
        Check if the output directory already exists
        """
        if not self.inputs.force:
            self.logger.info(
                f"Attempting to locate outputs from previous run in {self.inputs.output_directory}"
            )
            result = self._list_outputs()
            if all(Path(value).exists() for value in result.values()):
                self.logger.info(
                    f"Outputs already exist in {self.inputs.output_directory}. If you want to run the procedure again, set force=True."
                )
                return

    def _locate_fs_license_file(self):
        """
        Locate the FreeSurfer license file
        """
        if not isdefined(self.inputs.fs_license_file):
            fs_home = os.getenv("FREESURFER_HOME")
            if fs_home is None:
                raise ValueError(
                    "FREESURFER_HOME environment variable is not set and fs_license_file is not provided."
                )
            fs_license_file = Path(fs_home) / "license.txt"
            if not fs_license_file.exists():
                raise ValueError(
                    f"FreeSurfer license file not found at {fs_license_file}"
                )
            self.inputs.fs_license_file = str(Path(fs_home) / "license.txt")

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["output_directory"] = op.abspath(self.inputs.output_directory)
        return outputs

    def _set_up_directories(self):
        for participant_label in self.inputs.participant_label:
            base_dir = Path(self.inputs.output_directory) / f"sub-{participant_label}"
            (base_dir / "figures").mkdir(parents=True, exist_ok=True)
            (base_dir / "logs").mkdir(parents=True, exist_ok=True)
            for session in self.sessions:
                (base_dir / f"ses-{session}").mkdir(parents=True, exist_ok=True)
            if len(self.sessions) > 1:
                (base_dir / "anat").mkdir(parents=True, exist_ok=True)
            else:
                (base_dir / f"ses-{self.sessions[0]}" / "anat").mkdir(
                    parents=True, exist_ok=True
                )

    @property
    def sessions(self):
        """
        Get the sessions
        """
        return [
            session.name.split("-")[-1]
            for session in Path(self.inputs.input_directory).glob("ses-*")
            if session.is_dir()
        ]

# tests/procedures/procedure/mock_procedure.py

from pathlib import Path

from src.yalab_procedures.procedures.procedure import Procedure


class MockProcedure(Procedure):
    def run_procedure(self, **kwargs):
        self.logger.info("Running the mock procedure")
        # Simulate some processing
        output_dir = Path(kwargs["output_directory"])
        output_dir.mkdir(parents=True, exist_ok=True)

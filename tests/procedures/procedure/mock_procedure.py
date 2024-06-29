# tests/procedures/procedure/mock_procedure.py

from src.yalab_procedures.procedures.procedure import Procedure


class MockProcedure(Procedure):
    def run_procedure(self, input_dir, output_dir, config, logging_dest):
        self.logger.info("Running the mock procedure")
        # Simulate some processing
        output_dir.mkdir(parents=True, exist_ok=True)

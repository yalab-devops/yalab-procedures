# tests/procedure/mock_procedure.py
from src.yalab_procedures.procedures.procedure import Procedure


class MockProcedure(Procedure):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def run(self) -> None:
        self.log("Running the mock procedure.")

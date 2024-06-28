# tests/procedure/mock_procedure.py
from src.yalab_procedures.procedure.procedure import (  # Adjust the import according to your project structure
    Procedure,
)


class MockProcedure(Procedure):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def run(self) -> None:
        self.log("Running the mock procedure.")

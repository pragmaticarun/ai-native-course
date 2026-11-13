from aincourse import AssistantTurn


class TokenMeter:
    def record(self, turn: AssistantTurn) -> None:
        pass  # TODO

    @property
    def total(self) -> tuple[int, int]:
        return (0, 0)

    @property
    def calls(self) -> int:
        return 0

    def mean_per_call(self) -> tuple[float, float]:
        return (0.0, 0.0)

    def most_expensive(self, input_weight: float = 1.0, output_weight: float = 4.0) -> int | None:
        return None

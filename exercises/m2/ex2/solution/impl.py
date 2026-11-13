from aincourse import AssistantTurn


class TokenMeter:
    def __init__(self) -> None:
        self._turns: list[tuple[int, int]] = []

    def record(self, turn: AssistantTurn) -> None:
        self._turns.append((turn.input_tokens, turn.output_tokens))

    @property
    def total(self) -> tuple[int, int]:
        return (sum(i for i, _ in self._turns), sum(o for _, o in self._turns))

    @property
    def calls(self) -> int:
        return len(self._turns)

    def mean_per_call(self) -> tuple[float, float]:
        if not self._turns:
            return (0.0, 0.0)
        i, o = self.total
        return (i / self.calls, o / self.calls)

    def most_expensive(self, input_weight: float = 1.0, output_weight: float = 4.0) -> int | None:
        if not self._turns:
            return None
        costs = [i * input_weight + o * output_weight for i, o in self._turns]
        return costs.index(max(costs))

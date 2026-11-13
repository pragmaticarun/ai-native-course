"""L6.2: the same idea in Inspect AI (UK AISI's eval framework), offline.

Inspect's built-in `mockllm/model` provider returns outputs we script, so the
task runs in CI with no API key. Tested with inspect-ai 0.3.289.
Swap `model=` for a real provider id to run it live (not exercised in CI).
"""

from __future__ import annotations

from inspect_ai import Task, eval, task
from inspect_ai.dataset import Sample
from inspect_ai.model import ModelOutput, get_model
from inspect_ai.scorer import includes
from inspect_ai.solver import generate

QUESTIONS = [
    ("Which ffmpeg flag copies streams without re-encoding?", "-c copy"),
    ("Which adb command dumps the UI hierarchy?", "uiautomator dump"),
    ("What does LUFS measure?", "loudness"),
]


@task
def course_facts() -> Task:
    return Task(
        dataset=[Sample(input=q, target=a) for q, a in QUESTIONS],
        solver=[generate()],
        scorer=includes(),
    )


def run_offline(answers: list[str], log_dir: str) -> float:
    model = get_model(
        "mockllm/model",
        custom_outputs=[
            ModelOutput.from_content(model="mockllm/model", content=a) for a in answers
        ],
    )
    logs = eval(
        course_facts(), model=model, log_dir=log_dir, display="none", max_tasks=1, max_samples=1
    )
    return logs[0].results.scores[0].metrics["accuracy"].value  # type: ignore[union-attr]


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        print(
            "accuracy:",
            run_offline(["Use -c copy.", "adb shell uiautomator dump", "Perceived pitch"], d),
        )

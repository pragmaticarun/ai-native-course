from _impl import load

from aincourse import AssistantTurn, Message, ScriptedModel

impl = load(__file__)


def test_empty():
    m = impl.TokenMeter()
    assert (m.total, m.calls, m.mean_per_call(), m.most_expensive()) == (
        (0, 0),
        0,
        (0.0, 0.0),
        None,
    )


def test_totals_means_and_weighting():
    m = impl.TokenMeter()
    for i, o in [(100, 10), (50, 40), (100, 10)]:
        m.record(AssistantTurn(input_tokens=i, output_tokens=o))
    assert m.total == (250, 60) and m.calls == 3
    assert m.mean_per_call() == (250 / 3, 20.0)
    assert m.most_expensive() == 1  # 50 + 160 beats 100 + 40
    assert m.most_expensive(output_weight=1.0) == 0  # tie-free: 110 vs 90 vs 110 -> first


def test_input_grows_as_conversation_is_resent():
    model = ScriptedModel([AssistantTurn(text="x" * 40)] * 3)
    meter, messages = impl.TokenMeter(), [Message("user", "y" * 400)]
    for _ in range(3):
        turn = model.complete(messages)
        meter.record(turn)
        messages.append(turn.as_message())
    assert meter.calls == 3
    assert meter.total[0] > 3 * 100  # later calls pay for earlier turns again

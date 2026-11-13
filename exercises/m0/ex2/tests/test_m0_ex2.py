from _impl import load

from aincourse import Message, ToolSpec

impl = load(__file__)
GET_TIME = ToolSpec("get_time", "Current time in a time zone", {"type": "object"})


def drive(model, fake_time: str) -> str:
    messages = [Message("user", "What time is it in Kolkata?")]
    turn = model.complete(messages, [GET_TIME])
    for _ in range(3):
        if not turn.tool_calls:
            return turn.text
        messages.append(turn.as_message())
        for call in turn.tool_calls:
            assert call.name == "get_time" and call.arguments == {"tz": "Asia/Kolkata"}
            messages.append(Message("tool", fake_time, tool_call_id=call.id))
        turn = model.complete(messages, [GET_TIME])
    raise AssertionError("model never answered")


def test_tool_call_then_answer():
    assert drive(impl.make_scripted_model(), "21:30") == "It is 21:30 in Kolkata."


def test_answer_uses_the_tool_result():
    assert drive(impl.make_scripted_model(), "06:05") == "It is 06:05 in Kolkata."

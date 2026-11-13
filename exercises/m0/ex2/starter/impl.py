from aincourse import AssistantTurn, ScriptedModel


def make_scripted_model() -> ScriptedModel:
    # TODO: return a tool call first, then a text answer built from the tool result.
    return ScriptedModel([AssistantTurn(text="I don't know the time.")])

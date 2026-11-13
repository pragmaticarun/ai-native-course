from pydantic import BaseModel, Field

from aincourse import ChatModel, Message, ToolSpec

FACTORS = {("km", "mi"): 0.621371, ("mi", "km"): 1.609344}


class ConvertArgs(BaseModel, extra="forbid"):
    value: float = Field(gt=0)
    from_unit: str = Field(pattern="^(km|mi)$")
    to_unit: str = Field(pattern="^(km|mi)$")


CONVERT = ToolSpec("convert", "Convert km<->mi", ConvertArgs.model_json_schema())


def convert(args: ConvertArgs) -> float:
    return round(args.value * FACTORS[(args.from_unit, args.to_unit)], 4)


def convert_with_repair(model: ChatModel, question: str, max_attempts: int = 3) -> str:
    from pydantic import ValidationError

    messages = [Message("user", question)]
    attempts = 0
    turn = model.complete(messages, [CONVERT])
    while turn.tool_calls:
        messages.append(turn.as_message())
        for call in turn.tool_calls:
            attempts += 1
            try:
                result = str(convert(ConvertArgs.model_validate(call.arguments)))
            except ValidationError as err:
                if attempts >= max_attempts:
                    raise RuntimeError(f"no valid arguments after {attempts} attempts") from err
                result = f"error: invalid arguments: {err}"
            messages.append(Message("tool", result, tool_call_id=call.id))
        turn = model.complete(messages, [CONVERT])
    return turn.text

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
    # TODO: validate tool arguments, send errors back as tool results, retry.
    turn = model.complete([Message("user", question)], [CONVERT])
    return turn.text

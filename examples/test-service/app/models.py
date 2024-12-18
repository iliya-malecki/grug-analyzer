from pydantic import BaseModel

class InputModel(BaseModel):
    input: str

class OutputModel(BaseModel):
    output: str

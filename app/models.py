from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(max_length=4000)


class ChatResponse(BaseModel):
    answer: str
    trace_id: str | None

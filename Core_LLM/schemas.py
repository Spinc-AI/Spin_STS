"""Pydantic request/response models for the Core_LLM HTTP API."""
from pydantic import BaseModel


class ChatMessage(BaseModel):
    """One message in the standard OpenAI chat format."""
    role: str       # "system" | "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    temperature: float = 0.3


class ChatResponse(BaseModel):
    reply: str


class ChatAudioResponse(BaseModel):
    reply: str


class HealthResponse(BaseModel):
    status: str
    model: str
    loaded: bool

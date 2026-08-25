"""Pydantic request/response models for the Core_LLM HTTP API."""
from pydantic import BaseModel


class ChatMessage(BaseModel):
    """One message in the standard OpenAI chat format."""
    role: str       # "system" | "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    model: str | None = None        # registry key -- falls back to config.DEFAULT_MODEL
    temperature: float = 0.3


class ChatResponse(BaseModel):
    model: str
    reply: str


class ChatAudioResponse(BaseModel):
    model: str
    reply: str


class HealthResponse(BaseModel):
    status: str
    model: str | None = None   # currently loaded registry key, or None if nothing's loaded yet


class ModelsResponse(BaseModel):
    available: list[str]
    loaded: str | None = None

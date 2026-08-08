"""Pydantic response models for the Core_LLM HTTP API."""
from pydantic import BaseModel


class ChatAudioResponse(BaseModel):
    reply: str


class HealthResponse(BaseModel):
    status: str
    model: str
    loaded: bool

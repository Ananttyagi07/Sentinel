from pydantic import BaseModel, Field
from typing import Annotated
from langgraph.graph.message import add_messages
import uuid

class ResearchState(BaseModel):
    url: str
    page_content: str
    query: str
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    research_plan: list[str] = []
    search_results: list[dict] = []
    synthesis: str = ""
    messages: Annotated[list, add_messages] = []

class SyncState(BaseModel):
    url: str
    page_content: str
    page_title: str
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    page_type: str = ""
    tags: list[str] = []
    summary: str = ""
    insights: list[str] = []
    notion_page_id: str = ""
    already_synced: bool = False
    messages: Annotated[list, add_messages] = []

class ChatState(BaseModel):
    url: str
    page_content: str
    message: str
    history: list[dict] = []
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    response: str = ""
    needs_search: bool = False
    search_results: list[dict] = []
    messages: Annotated[list, add_messages] = []
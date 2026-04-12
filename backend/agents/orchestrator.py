import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver

from agents.graph import build_chat_graph, build_research_graph, build_sync_graph
from tools.tavily_tools import TavilyTools
from tools.notion_tools import NotionTools
from tools.page_rag import SessionPageRAG

load_dotenv()

def create_graph():
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    memory = MemorySaver()
    tavily = TavilyTools()
    notion = NotionTools()
    rag = SessionPageRAG()
    
    return {
        "researcher": build_research_graph(llm, tavily, memory),
        "sync": build_sync_graph(llm, notion, memory),
        "chat": build_chat_graph(llm, tavily, rag, memory)
    }
    
async def run_research(graphs, url, page_content, query, session_id):
    config = {"configurable": {"thread_id": f"{session_id}-research"}}
    state = await graphs["researcher"].ainvoke(
        {"url": url, "page_content": page_content, "query": query, "messages": []},
        config
    )
    return {
        "synthesis": state["synthesis"],
        "sources": [r.get("url") for r in state.get("search_results", [])],
        "plan": state.get("research_plan", []),
    }
    
async def run_notion_sync(graphs, url, page_content, page_title, session_id):
    config = {"configurable": {"thread_id": f"{session_id}-sync"}}
    state = await graphs["sync"].ainvoke(
        {"url": url, "page_content": page_content, "page_title": page_title, "messages": []},
        config
    )
    if state.get("already_synced"):
        return {"status": "already_synced", "message": "This page was already saved to Notion."}
    return {
        "status":         "synced",
        "notion_page_id": state.get("notion_page_id"),
        "summary":        state.get("summary"),
        "tags":           state.get("tags", []),
        "insights":       state.get("insights", []),
    }

async def run_chat(graphs, url, page_content, message, history, session_id):
    print("From chat orchestrator.py, run_chat params: ", message)
    config = {"configurable": {"thread_id": f"{session_id}-chat"}}
    state = await graphs["chat"].ainvoke(
        {
            "url": url,
            "page_content": page_content,
            "message": message,
            "history": history,
            "session_id": session_id,
            "messages": [],
        },
        config
    )
    print("From chat orchestrator.py, run_chat, llm response: ", state.get("response", "No response generated"))
    return state.get("response", "") if isinstance(state, dict) else state.response

async def stream_chat(graphs, url, page_content, message, history, session_id):
    config = {"configurable": {"thread_id": f"{session_id}-chat-stream"}}
    async for chunk in graphs["chat"].astream(
        {
            "url": url,
            "page_content": page_content,
            "message": message,
            "history": history,
            "session_id": session_id,
            "messages": [],
        },
        config=config,
    ):
        if "responder" in chunk:
            response = chunk["responder"].get("response", "")
            if response:
                yield json.dumps({"chunk": response})
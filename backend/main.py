import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from agents.states import SyncState, ChatState, ResearchState
from agents.orchestrator import create_graph, run_chat, run_notion_sync, run_research, stream_chat

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

graphs: dict | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global graphs
    graphs = create_graph()
    logger.info("AI-Extension graphs initialized")
    yield
    logger.info("Shutting down extension...")

app = FastAPI(
    title="AI-Extension",
    description="Agentic Browser Extension -- Powered by LangGraph",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/research")
async def deep_research(req: ResearchState):
    try:
        result = await run_research(
            graphs=graphs,
            url=req.url,
            page_content=req.page_content,
            query=req.query,
            session_id=req.session_id
        )
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Research error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sync")
async def notion_sync(req: SyncState):
    try:
        result = await run_notion_sync(
            graphs=graphs,
            url=req.url,
            page_content=req.page_content,
            page_title=req.page_title,
            session_id=req.session_id,
        )
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat(req: ChatState):
    try:
        result = await run_chat(
            graphs=graphs,
            url=req.url,
            page_content=req.page_content,
            message=req.message,
            history=req.history,
            session_id=req.session_id,
        )
        print("")
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
async def chat_stream(req: ChatState):
    async def generate():
        async for chunk in stream_chat(
            graphs=graphs,
            url=req.url,
            page_content=req.page_content,
            message=req.message,
            history=req.history,
            session_id=req.session_id,
        ):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
# Sentinel - Agentic Browser Architect

Sentinel is an AI-powered browser extension + backend system for context-aware chat, deep research, and Notion knowledge sync.

It reads the active page content in your browser, routes requests through specialized LangGraph workflows, and returns structured outputs for three core actions:

- Chat with page-aware context and optional live web search
- Run deep research with planning, search, and synthesis
- Sync page insights into Notion with duplicate detection

## Features

- Browser side panel UX with Chat, Research, and Notion tabs
- FastAPI backend with dedicated endpoints for each workflow
- Multi-graph orchestration using LangGraph state machines
- Session-aware retrieval with ChromaDB for grounded responses
- Tavily web search integration for live information retrieval
- Notion integration for structured storage (summary, tags, insights)
- Safety/fallback behavior when external keys are missing

## Demo Video
https://github.com/user-attachments/assets/3f17415c-9209-413c-80bc-7a4092a9f9c2

## Architecture

### Extension layer (Chrome, Manifest V3)

- Side panel UI: user inputs and response rendering
- Background service worker: message routing + API calls
- Content extraction: URL, title, and visible page text

### Backend layer (FastAPI + LangGraph)

- `/chat`: context-aware answers using page RAG and optional search
- `/research`: planner -> searcher -> synthesizer pipeline
- `/sync`: classifier -> duplicate check -> analyzer -> Notion writer
- `/chat/stream`: SSE streaming for chat responses

### Data and memory

- Per-session graph checkpoints via LangGraph `MemorySaver`
- Per-session page indexing in ChromaDB for retrieval-grounded answers
- Session IDs propagated from extension to backend endpoints

## Tech Stack

- Frontend: Chrome Extension (Manifest V3), Vanilla JS, CSS
- Backend: Python 3.12+, FastAPI, Uvicorn
- AI orchestration: LangGraph, LangChain, OpenAI
- Retrieval: ChromaDB + OpenAI embeddings (`text-embedding-3-small`)
- Search: Tavily
- Knowledge sync: Notion API

## Project Structure

```text
ai-extension/
  backend/
    main.py
    pyproject.toml
    agents/
      graph.py
      orchestrator.py
      states.py
      nodes/
        chat_node.py
        research_node.py
        sync_node.py
    tools/
      notion_tools.py
      page_rag.py
      tavily_tools.py
  extension/
    manifest.json
    src/
      background.js
      content.js
      panel.html
      panel.css
      panel.js
```

## Prerequisites

- Python 3.12+
- Chrome (or Chromium-based browser that supports side panel extensions)
- OpenAI API key

Optional (feature-specific):

- Tavily API key for live web research/search
- Notion API key + Notion database ID for sync

## Environment Variables

Create a `.env` file inside `backend/`:

```env
OPENAI_API_KEY=your_openai_key
TAVILY_API_KEY=your_tavily_key
NOTION_API_KEY=your_notion_integration_key
NOTION_DATABASE_ID=your_notion_database_id
```

Behavior when keys are missing:

- Missing `TAVILY_API_KEY`: search returns mock results
- Missing `NOTION_API_KEY`: Notion sync runs in mock mode
- Missing `NOTION_DATABASE_ID` with Notion key set: sync will fail

## Setup and Run

### 1) Backend

From the project root:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e .
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at:

- `http://localhost:8000`

### 2) Extension

1. Open Chrome and go to `chrome://extensions`
2. Enable Developer Mode
3. Click Load unpacked
4. Select the `extension/` folder
5. Pin Sentinel and open the side panel from the toolbar action

The extension is configured to call the backend at:

- `http://localhost:8000`

## Workflow Summary

- Chat pipeline:
  - Intent router decides if web search is needed
  - Optional Tavily search enriches context
  - Session RAG retrieves relevant page chunks
  - Responder returns grounded answer

- Research pipeline:
  - Planner generates focused search queries
  - Searcher collects external evidence
  - Synthesizer creates a structured response with sources

- Sync pipeline:
  - Classifier identifies page type
  - Duplicate checker avoids repeated Notion entries
  - Analyzer extracts summary/tags/insights
  - Writer creates structured Notion page


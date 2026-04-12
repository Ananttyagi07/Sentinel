import json
import re
from langchain_core.messages import HumanMessage


def _parse_llm_json(content) -> dict:
    text = str(content or "")
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, re.IGNORECASE)
    if match:
        try:
            parsed = json.loads(match.group(1))
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(text[start:end + 1])
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

    return {}

async def sync_classifier(state, llm):
    prompt = f"""Classify this webpage type. URL: {state.url}
                 Title: {state.page_title}
                 Content (first 500 chars): {state.page_content[:500]}
                 
                 Return JSON: {{"page_type": "article|product|documentation|news|other"}}"""
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    data = _parse_llm_json(response.content)
    page_type = str(data.get("page_type", "other"))
    return {"page_type": page_type}

async def sync_duplicate_check(state, notion):
    already_synced = await notion.check_duplicate(state.url)
    return {"already_synced": already_synced}

async def sync_analyzer(state, llm):
    prompt = f"""Analyze this {state.page_type} page and extract structured information.

                 Title: {state.page_title}
                 URL: {state.url}
                 Content: {state.page_content[:3000]}
                 
                 Return JSON:
                 {{
                   "summary": "2-3 sentence summary",
                   "tags": ["tag1", "tag2", "tag3"],
                   "insights": ["key insight 1", "key insight 2", "key insight 3"]
                 }}"""
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    print("This is the output generated for notion sync: ", response)
    data = _parse_llm_json(response.content)
    if not data:
        data = {"summary": state.page_content[:200], "tags": [], "insights": []}

    return {
        "summary": str(data.get("summary", state.page_content[:200])),
        "tags": [str(tag) for tag in data.get("tags", [])][:5],
        "insights": [str(item) for item in data.get("insights", [])][:10],
    }

async def sync_notion_writer(state, notion):
    page_id = await notion.create_page(
        title=state.page_title,
        url=state.url,
        page_type=state.page_type,
        summary=state.summary,
        tags=state.tags,
        insights=state.insights
    )
    return {"notion_page_id": page_id}

async def sync_skip(state):
    return {"notion_page_id": "already_exists"}
import json
from langchain_core.messages import HumanMessage, SystemMessage

async def chat_intent_router(state, llm):
    prompt = f"""Does this question require a live web search to answer accurately?
                Question: {state.message}
                Page URL: {state.url}

                Return JSON: {{"needs_search": true|false, "reason": "brief reason"}}"""
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    try:
        data = json.loads(response.content)
        needs_search = data.get("needs_search", False)
    except Exception:
        needs_search = False
    return {"needs_search": needs_search}

async def chat_searcher(state, tavily):
    results = await tavily.search(state.message)
    return {"search_results": results}

async def chat_responder(state, llm, rag):
    search_ctx = ""
    if state.search_results:
        search_ctx = "\n\nWeb Search Results:\n" + "\n".join([
            f"- {r.get('title')}: {r.get('content', '')[:200]}"
            for r in state.search_results[:4]
        ])

    rag_status = rag.ensure_page_index(
        session_id=state.session_id,
        url=state.url,
        page_content=state.page_content,
    )
    retrieved_chunks = rag.query_page(session_id=state.session_id, query=state.message, top_k=6)
    page_ctx = "\n\n---\n\n".join(retrieved_chunks) if retrieved_chunks else state.page_content[:2000]
    retrieval_note = f"RAG status: {rag_status.get('status', 'unknown')}"

    history_text = "\n".join([
        f"{m['role'].capitalize()}: {m['content']}"
        for m in (state.history or [])[-6:]
    ])

    system = f"""You are Sentinel, an intelligent browser assistant. You have access to the current webpage.
                Current Page: {state.url}
                Relevant Page Chunks (retrieved by RAG):
                {page_ctx}
                {retrieval_note}
                {search_ctx}"""
    
    messages = [SystemMessage(content=system)]
    if history_text:
        messages.append(HumanMessage(content=f"Previous conversation:\n{history_text}"))
    messages.append(HumanMessage(content=state.message))

    response = await llm.ainvoke(messages)
    return {"response": response.content}
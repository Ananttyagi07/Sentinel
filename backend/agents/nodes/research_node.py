import json
from langchain_core.messages import HumanMessage

async def research_planner(state, llm):
    prompt = f"""You are a research planner. Given a webpage and a query, create a focused research plan.

                URL: {state.url}
                Query: {state.query}
                Page Summary (first 2000 chars): {state.page_content[:2000]}

                Generate 3-5 specific search queries to answer the user's question comprehensively.
                Return as JSON: {{"queries": ["query1", "query2", ...]}}"""
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    try:
        data = json.loads(response.content)
        plan = data.get("queries", [state.query])
    except Exception:
        plan = [state.query]
    
    return {"research_plan": plan}

async def reseach_searcher(state, tavily):
    results = []
    for query in state.research_plan[:2]:
        try:
            result = await tavily.search(query)
            results.extend(result)
        except Exception as e:
            print(f"Search failed for '{query}': {e}")
    return {"search_results": results}

async def research_synthesizer(state, llm):
    results_text = "\n\n".join([
        f"**{r.get('title', 'Result')}**\n{r.get('content', '')}\nSource: {r.get('url', '')}"
        for r in state.search_results[:6]
    ])

    prompt = f"""Synthesize these research results into a clear, structured answer.

                Original Query: {state.query}
                Page Context: {state.page_content[:1000]}

                Research Results:
                {results_text}

                Provide a comprehensive, well-structured response with key findings and source attribution."""
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return {"synthesis": response.content}
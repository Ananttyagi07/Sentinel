from functools import partial
from langgraph.graph import StateGraph, END

from agents.states import ResearchState, SyncState, ChatState
from agents.nodes.research_node import reseach_searcher, research_planner, research_synthesizer
from agents.nodes.sync_node import sync_analyzer, sync_classifier, sync_duplicate_check, sync_notion_writer, sync_skip
from agents.nodes.chat_node import chat_intent_router, chat_responder, chat_searcher

def build_research_graph(llm, tavily, memory):
    graph = StateGraph(ResearchState)
    
    graph.add_node("planner", partial(research_planner, llm=llm))
    graph.add_node("searcher", partial(reseach_searcher, tavily=tavily))
    graph.add_node("synthesizer", partial(research_synthesizer, llm=llm))

    graph.set_entry_point("planner")
    graph.add_edge("planner", "searcher")
    graph.add_edge("searcher", "synthesizer")
    graph.add_edge("synthesizer", END)

    return graph.compile(checkpointer=memory)

def build_sync_graph(llm, notion, memory):
    graph = StateGraph(SyncState)

    graph.add_node("classifier", partial(sync_classifier, llm=llm))
    graph.add_node("duplicate_check", partial(sync_duplicate_check, notion=notion))
    graph.add_node("analyzer", partial(sync_analyzer, llm=llm))
    graph.add_node("notion_writer", partial(sync_notion_writer, notion=notion))
    graph.add_node("skip", sync_skip)

    graph.set_entry_point("classifier")
    graph.add_edge("classifier", "duplicate_check")
    graph.add_conditional_edges(
        "duplicate_check",
        lambda s: "skip" if s.already_synced else "analyzer"
    )
    graph.add_edge("analyzer", "notion_writer")
    graph.add_edge("notion_writer", END)
    graph.add_edge("skip", END)

    return graph.compile(checkpointer=memory)

def build_chat_graph(llm, tavily, rag, memory):
    graph = StateGraph(ChatState)
    
    graph.add_node("intent_router", partial(chat_intent_router, llm=llm))
    graph.add_node("searcher", partial(chat_searcher, tavily=tavily))
    graph.add_node("responder", partial(chat_responder, llm=llm, rag=rag))

    graph.set_entry_point("intent_router")
    graph.add_conditional_edges(
        "intent_router",
        lambda s: "searcher" if s.needs_search else "responder",
    )
    graph.add_edge("searcher", "responder")
    graph.add_edge("responder", END)

    return graph.compile(checkpointer=memory)
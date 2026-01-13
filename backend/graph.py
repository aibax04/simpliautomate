from typing import TypedDict, List, Annotated, Optional
from langgraph.graph import StateGraph, END
from backend.agents.news_fetch_agent import NewsFetchAgent
from backend.agents.curation_agent import CurationAgent

class GraphState(TypedDict):
    news_items: List[dict]
    current_index: int
    selected_news: dict
    generated_content: str
    status: str
    search_query: Optional[str]


async def fetch_news_node(state: GraphState):
    query = state.get("search_query")
    if query:
        print(f"--- SEARCHING FOR: {query} ---")
    else:
        print("--- FETCHING LIVE NEWS ---")
        
    fetcher = NewsFetchAgent()
    items = await fetcher.fetch(query=query)
    
    curator = CurationAgent()
    curated_items = curator.curate(items)
    
    return {"news_items": curated_items, "status": "news_ready"}

def create_graph():
    workflow = StateGraph(GraphState)
    
    # Define the nodes
    workflow.add_node("fetch_news", fetch_news_node)
    
    # Define edges
    workflow.set_entry_point("fetch_news")
    workflow.add_edge("fetch_news", END)
    
    return workflow.compile()

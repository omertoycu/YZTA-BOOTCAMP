from functools import partial

from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from app.agents.matching import matching_node
from app.agents.state import AgentState


def build_matching_graph(db: Session):
    """Sprint 1 MVP: tek node'lu graf. Sprint 2+'da intake/scoring/pricing node'ları eklenecek."""
    graph = StateGraph(AgentState)
    graph.add_node("matching", partial(matching_node, db=db))
    graph.set_entry_point("matching")
    graph.add_edge("matching", END)
    return graph.compile()

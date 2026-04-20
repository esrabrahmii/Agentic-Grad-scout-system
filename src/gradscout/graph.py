"""LangGraph graph assembly — wires all nodes together."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from gradscout.nodes.discover import discover_node
from gradscout.nodes.intake import intake_node
from gradscout.nodes.output import output_node
from gradscout.nodes.rank import rank_node
from gradscout.nodes.research import research_node, should_continue_research
from gradscout.state import AgentState


def build_graph():
    """Build and compile the grad-scout LangGraph agent."""
    builder = StateGraph(AgentState)

    # Register nodes
    builder.add_node("intake", intake_node)
    builder.add_node("discover", discover_node)
    builder.add_node("research", research_node)
    builder.add_node("rank", rank_node)
    builder.add_node("output", output_node)

    # Linear edges
    builder.add_edge(START, "intake")
    builder.add_edge("intake", "discover")
    builder.add_edge("discover", "research")

    # Research loop: keep calling research_node until all programs are processed
    builder.add_conditional_edges(
        "research",
        should_continue_research,
        {
            "research": "research",  # loop back
            "rank": "rank",          # move forward
        },
    )

    builder.add_edge("rank", "output")
    builder.add_edge("output", END)

    return builder.compile()


# Singleton — import this in the UI and CLI
graph = build_graph()

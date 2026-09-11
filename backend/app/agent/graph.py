"""
LangGraph StateGraph Definition
Wires together all nodes with conditional routing.

Graph flow:
  START
    │
    ▼
  classify_intent
    │
    ├─ "log"      → log_complaint      → risk_assessment → completeness_check → END
    ├─ "edit"     → edit_complaint     → risk_assessment → completeness_check → END
    ├─ "document" → document_extract   → risk_assessment → completeness_check → END
    └─ "query"    → query_answer                                               → END
"""
from typing import Literal
from langgraph.graph import StateGraph, END, START
from app.agent.state import AgentState
from app.agent.nodes import (
    classify_intent_node,
    log_complaint_node,
    edit_complaint_node,
    document_extract_node,
    risk_assessment_node,
    query_answer_node,
    completeness_check_node,
)


# ── Router: After intent classification ──────────────────────────────────────

def route_by_intent(
    state: AgentState,
) -> Literal["log_complaint", "edit_complaint", "document_extract", "query_answer"]:
    """
    Reads the 'intent' field set by classify_intent_node and routes
    to the appropriate tool node. Kept simple — no LLM calls here.
    """
    intent = state.get("intent", "log")
    mapping = {
        "log": "log_complaint",
        "edit": "edit_complaint",
        "document": "document_extract",
        "query": "query_answer",
    }
    return mapping.get(intent, "log_complaint")


# ── Router: After extraction — skip risk_assessment if there's an error ───────

def route_after_extraction(
    state: AgentState,
) -> Literal["risk_assessment", "completeness_check"]:
    """
    If extraction succeeded (no error), proceed to risk assessment.
    If there was an error, skip straight to completeness check (which will show the error).
    """
    if state.get("error"):
        return "completeness_check"
    return "risk_assessment"


# ── Build the Graph ──────────────────────────────────────────────────────────

def build_complaint_graph() -> StateGraph:
    """
    Construct and compile the LangGraph StateGraph.
    Returns a compiled graph ready for invocation.
    """
    workflow = StateGraph(AgentState)

    # Register nodes
    workflow.add_node("classify_intent", classify_intent_node)
    workflow.add_node("log_complaint", log_complaint_node)
    workflow.add_node("edit_complaint", edit_complaint_node)
    workflow.add_node("document_extract", document_extract_node)
    workflow.add_node("risk_assessment", risk_assessment_node)
    workflow.add_node("query_answer", query_answer_node)
    workflow.add_node("completeness_check", completeness_check_node)

    # Entry point
    workflow.add_edge(START, "classify_intent")

    # Conditional routing after intent classification
    workflow.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "log_complaint": "log_complaint",
            "edit_complaint": "edit_complaint",
            "document_extract": "document_extract",
            "query_answer": "query_answer",
        },
    )

    # After each extraction type → conditional (error check) → risk or completeness
    for extraction_node in ["log_complaint", "edit_complaint", "document_extract"]:
        workflow.add_conditional_edges(
            extraction_node,
            route_after_extraction,
            {
                "risk_assessment": "risk_assessment",
                "completeness_check": "completeness_check",
            },
        )

    # After risk assessment → completeness check
    workflow.add_edge("risk_assessment", "completeness_check")

    # Terminals → END
    workflow.add_edge("completeness_check", END)
    workflow.add_edge("query_answer", END)

    return workflow.compile()


# ── Singleton graph instance (compiled once at startup) ────────────────────

complaint_graph = build_complaint_graph()

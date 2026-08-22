from langgraph.graph import StateGraph, END  # type: ignore
import os
from .state import AgentState  # type: ignore
from .nodes import (  # type: ignore
    ingest_node, detect_node, reason_node,
    reroute_node, coordination_node, alert_node, report_node,
    supervisor_node, evaluate_previous_action, predict_node
)

workflow = StateGraph(AgentState)
workflow.add_node("evaluate_previous_action", evaluate_previous_action)
workflow.add_node("ingest_node", ingest_node)
workflow.add_node("detect_node", detect_node)
workflow.add_node("predict_node", predict_node)
workflow.add_node("supervisor_node", supervisor_node)
workflow.add_node("reason_node", reason_node)
workflow.add_node("reroute_node", reroute_node)
workflow.add_node("coordination_node", coordination_node)
workflow.add_node("alert_node", alert_node)
workflow.add_node("report_node", report_node)

workflow.set_entry_point("evaluate_previous_action")

def route_from_supervisor(state: AgentState) -> str:
    next_node = state.get("next_node", "END")
    if next_node == "END":
        return END
    return next_node

workflow.add_edge("evaluate_previous_action", "ingest_node")
workflow.add_edge("ingest_node", "detect_node")
workflow.add_edge("detect_node", "predict_node")
workflow.add_edge("predict_node", "supervisor_node")

# All worker nodes return back to the supervisor.
#
# detect_node deliberately has NO edge here: it already reaches the supervisor
# through predict_node. Adding a second edge made detect_node fan out to two
# branches at once, both of which eventually wrote `next_node` in the same
# superstep, and LangGraph aborted the whole run with
# INVALID_CONCURRENT_GRAPH_UPDATE — so no cycle ever reached report_node and no
# incident was ever written.
workflow.add_edge("reason_node", "supervisor_node")
workflow.add_edge("reroute_node", "supervisor_node")
workflow.add_edge("coordination_node", "supervisor_node")
workflow.add_edge("alert_node", "supervisor_node")
workflow.add_edge("report_node", END)

# Supervisor dynamically dispatches
workflow.add_conditional_edges(
    "supervisor_node",
    route_from_supervisor,
    {
        "detect_node": "detect_node",
        "reason_node": "reason_node",
        "reroute_node": "reroute_node",
        "coordination_node": "coordination_node",
        "alert_node": "alert_node",
        "report_node": "report_node",
        END: END
    }
)

from langgraph.checkpoint.memory import MemorySaver
checkpointer = MemorySaver()
railmind_graph = workflow.compile(checkpointer=checkpointer)

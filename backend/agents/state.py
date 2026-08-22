from typing import TypedDict, List, Optional, Annotated
import operator

def append_to_list(a: Optional[List], b: Optional[List]) -> List:
    if a is None:
        a = []
    if b is None:
        b = []

    # Handle specific CLEAR token to empty the list
    if b and b[0] == "CLEAR":
        return []

    return a + b

class TrainAnomaly(TypedDict):
    train_number: str
    train_name: str
    anomaly_type: str  # "delay", "overcrowding", "track_fault", "cancellation"
    severity: str      # "low", "medium", "high", "critical"
    location: str
    delay_minutes: Optional[int]
    passenger_load: Optional[str]

class DepartmentTask(TypedDict):
    department: str    # "maintenance", "operations", "station_manager"
    task_description: str
    urgency: str
    action_required: str

class AgentState(TypedDict):
    raw_train_data: List[dict]
    anomalies: Annotated[List[TrainAnomaly], append_to_list]
    claude_reasoning: str
    reroute_plan: Optional[str]
    department_tasks: Annotated[List[DepartmentTask], operator.add]
    sms_alerts_sent: Annotated[List[str], append_to_list]
    incident_report: Optional[str]
    loop_count: int
    should_continue: bool
    last_api_call: str
    railways_latency_ms: int
    ai_latency_ms: int
    processed_trains: List[str]
    target_trains: List[str]
    # How many times the reasoner has been attempted this cycle. Bounds the
    # supervisor's retry when the model returns nothing usable, so a bad
    # response degrades to the heuristic path instead of spinning the graph.
    reason_attempts: int
    # Stages the supervisor has already dispatched in this cycle. A stage that
    # ran and produced nothing is finished, not something to dispatch again.
    dispatched: Annotated[List[str], append_to_list]
    errors: Annotated[List[str], append_to_list]
    next_node: str
    last_node_executed: str
    messages: Annotated[list, operator.add]
    tools_used: Annotated[List[str], append_to_list]
    detour_route: List[str]
    perception: Optional[dict]
    decision: Optional[dict]
    incident_history: Optional[List[dict]]
    prediction: Optional[dict]
    memory_used: Optional[str]


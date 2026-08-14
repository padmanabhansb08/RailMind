import asyncio
import os
import sys

# Ensure backend can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agents.graph import railmind_graph # type: ignore
from backend.agents.state import AgentState # type: ignore

async def main():
    print("--- Running Agentic Recovery and self-correction unit tests ---")

    # Set API key in test scope
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-dummy"

    from backend.agents.nodes import supervisor_node

    # We craft a mock anomaly where we forcefully test supervisor recovery
    initial_state = {
        "raw_train_data": [],
        "anomalies": [{
            "train_number": "9999",
            "train_name": "Test Conflict Train",
            "anomaly_type": "delay",
            "severity": "high",
            "location": "Kanpur Central",
            "destination": "Varanasi",
            "delay_minutes": 60,
            "passenger_load": "high"
        }],
        "claude_reasoning": '{"maintenance_task": "Kanpur restricted tracks fixing"}',
        "reroute_plan": "Dijkstra routed: Kanpur Central -> Varanasi (ETA 100 mins)",
        "department_tasks": [],
        "sms_alerts_sent": [],
        "incident_report": None,
        "loop_count": 0,
        "should_continue": False,
        "errors": []
    }

    # We invoke graph starting from Supervisor to see if it catches the conflict
    print("[TEST] Supervisor should catch 'Kanpur restricted' string in reasoning and error out.")
    state = await supervisor_node(initial_state)

    # Check if errors got populated and reasoning ran again
    print(f"Final state keys: {list(state.keys())}")
    errors = state.get("errors", [])

    assert len(errors) > 0, "Supervisor should append an error when Kanpur conflict is present"
    assert "conflicts" in errors[0], "Error message must describe the conflict"
    assert state.get("next_node") == "reason_node", "Supervisor must route back to reason_node"
    assert state.get("claude_reasoning") == "{}", "Supervisor must clear claude_reasoning to force re-evaluation"

    print(f"[SUCCESS] Supervisor correctly appended errors: {errors}")
    print(f"[INFO] New Claude Reasoning: {state.get('claude_reasoning')}")

async def test_tool_exception_recovery():
    print("\n--- Running Tool Exception Recovery Test ---")

    # Set API key in test scope
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-dummy"

    from unittest.mock import patch, MagicMock, AsyncMock
    from langchain_core.messages import AIMessage, ToolMessage
    import backend.services.ai_service as ai

    anomalies = [{
        "train_number": "12301",
        "train_name": "Rajdhani",
        "anomaly_type": "delay",
        "severity": "high",
        "location": "Kanpur Central",
        "delay_minutes": 60,
    }]

    class MockLLM:
        def __init__(self, *args, **kwargs):
            self.call_count = 0

        def bind_tools(self, tools):
            return self

        def with_structured_output(self, schema):
            mock_structured = AsyncMock()
            mock_structured.ainvoke.return_value = MagicMock(dict=lambda: {"incident_title": "Test Title", "situation_summary": "Test", "maintenance_task": "Test", "operations_task": "Test", "station_manager_task": "Test", "passenger_sms": "Test", "incident_summary": "Test"})
            return mock_structured

        async def ainvoke(self, messages):
            self.call_count += 1
            if self.call_count == 1:
                # First call: LLM decides to use tool
                return AIMessage(content="", tool_calls=[{"name": "query_line_capacity", "args": {"station": "Kanpur Central"}, "id": "toolu_123"}])
            else:
                # Second call: LLM returns text after seeing tool result
                # Check that the messages list contains the tool exception message
                found_exception = any(isinstance(m, ToolMessage) and "Simulated tool crash" in m.content for m in messages)
                assert found_exception, "Tool exception was not appended to messages"
                return AIMessage(content="Final Plan", tool_calls=[])

    with patch("backend.services.ai_service.llm_with_tools", new=MockLLM()):
        with patch("backend.services.ai_service.llm", new=MockLLM()):
            with patch.dict(ai.tool_map):
                # Replace the tool with an exception-raising mock
                mock_tool = AsyncMock()
                mock_tool.name = "query_line_capacity"
                mock_tool.ainvoke.side_effect = ValueError("Simulated tool crash: Line capacity database unavailable.")
                ai.tool_map["query_line_capacity"] = mock_tool

                result = await ai.reason_with_ai(anomalies)
                assert result and "incident_title" in result and len(result["incident_title"]) > 0, "Expected structured output or dynamic fallback to return valid title dict"

    print("[SUCCESS] Tool Exception Recovery executed successfully through mock.")

if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(test_tool_exception_recovery())

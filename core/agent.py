import os


def agent_node(state: AgentState):
    msgs = [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": f"From: {state['sender']}\nSubject: {state['subject']}\n\n{state['email_text']}"
        }
    ]
    resp = _model().invoke(msgs)
    return {"messages": [resp]}


# Tool executor
tools_node = ToolNode(TOOLS)


# Finalize: run guardrail; if invalid → escalate
def finalize_node(state: AgentState):
    final_text = ""
    for m in reversed(state.get("messages", [])):
        if getattr(m, "type", "") == "ai" and getattr(m, "content", None):
            final_text = m.content
            break

    if not final_text:
        return {"decision": "escalate", "validation_reason": "empty_draft"}

    val = llm_validate([], final_text)  # You can store ctx in state via callbacks and pass it here

    return {
        "decision": "send" if val.get("is_valid") else "escalate",
        "validation_reason": val.get("reason", "")
    }


# Graph wiring
graph = StateGraph(AgentState)

graph.add_node("agent", agent_node)
graph.add_node("tools", tools_node)
graph.add_node("finalize", finalize_node)

graph.set_entry_point("agent")

# If model asked for a tool -> run tools, else continue
graph.add_conditional_edges("agent", tools_condition)

# After tools, go back to agent (think-act cycle)
graph.add_edge("tools", "agent")

# When no more tools are requested, finalize
graph.add_edge("agent", "finalize")

graph.add_conditional_edges(
    "finalize",
    lambda s: s.get("decision", "escalate"),
    {"send": END, "escalate": END}
)

app = graph.compile()

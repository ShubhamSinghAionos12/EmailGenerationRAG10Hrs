"""
Agentic email handler with tool-calling and safety gates.
- Tools: rag_search, send_email, db_log_tool
- LangGraph loop lets the LLM do multi-step plans (think → tool → observe ...)
- Post-step validator (guardrails) decides send vs escalate
"""
import os
from typing import TypedDict, List
from langchain_groq import ChatGroq
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph import StateGraph, END

from .tools import rag_search, send_email, db_log_tool
from .guardrails import llm_validate

# ----------------------------
# Config
# ----------------------------
MAX_TOOL_LOOPS = 6  # hard cap to avoid infinite cycles
MODEL_NAME = os.getenv("GROQ_MODEL", "llama3-8b-8192")

# ----------------------------
# Agent State
# ----------------------------
class AgentState(TypedDict, total=False):
    email_id: int
    sender: str
    subject: str
    email_text: str

    # running conversation with the LLM + tool results
    messages: list

    # knowledge context collected via rag_search tool
    ctx_docs: List[str]

    # loop counter to prevent infinite tool use
    loops: int

    # outcome
    decision: str            # "send" | "escalate"
    validation_reason: str

# ----------------------------
# Model + Policy
# ----------------------------
SYSTEM = (
    "You are an airline support agent. Decide if a question is within airline policy. "
    "If out-of-policy/ambiguous, CALL db_log_tool with reason and respond 'HUMAN_ESCALATION_NEEDED'. "
    "If in-policy, first CALL rag_search to gather context, then compose a concise plain-text reply. "
    "Only CALL send_email after you are confident. Keep answers grounded ONLY in rag_search context. "
    "Never invent policy. If context is insufficient after attempts, escalate."
)

def _model():
    # Bind tools so the model can function-call them autonomously
    return ChatGroq(model=MODEL_NAME, temperature=0).bind_tools([rag_search, send_email, db_log_tool])

# ----------------------------
# Nodes
# ----------------------------
def agent_node(state: AgentState):
    """Let the model decide the next action (may request a tool)."""
    loops = state.get("loops", 0)
    if loops > MAX_TOOL_LOOPS:
        # too many iterations; escalate safely
        return {"decision": "escalate", "validation_reason": "max_loops"}

    # Build a minimal convo each turn: system + user email + prior tool/assistant traces
    msgs = [{"role": "system", "content": SYSTEM}]

    # Provide the original email as the user message once; subsequent turns still include it
    user_blob = f"From: {state['sender']}\nSubject: {state['subject']}\n\n{state['email_text']}"
    msgs.append({"role": "user", "content": user_blob})

    # Add prior messages (assistant thoughts + tool results) so the model can continue planning
    if state.get("messages"):
        msgs.extend(state["messages"])  # ToolNode appends tool results back into messages list

    resp = _model().invoke(msgs)  # may carry a tool call

    # Stash the new assistant step; increment loop if it asked for a tool (handled by ToolNode)
    out = {
        "messages": (state.get("messages", []) + [resp]),
        "loops": loops + 1,
    }
    return out

# Executes whichever tool the last assistant message requested, and appends the tool result
# back into the messages list so the model can observe its outcome on the next agent_node call.
tools_node = ToolNode([rag_search, send_email, db_log_tool])

def collect_context_node(state: AgentState):
    """Scrape tool outputs from messages to keep a clean ctx_docs list for validator."""
    ctx = state.get("ctx_docs", [])
    for m in state.get("messages", [])[-4:]:  # look at most recent few messages
        # LangChain tool result messages usually expose a .name and .content
        name = getattr(m, "name", None) or getattr(m, "additional_kwargs", {}).get("name")
        if name == "rag_search":
            content = getattr(m, "content", "")
            # content is typically a stringified list; be permissive
            try:
                import json
                res = json.loads(content)
                if isinstance(res, list):
                    for d in res:
                        if isinstance(d, str) and d not in ctx:
                            ctx.append(d)
            except Exception:
                if content and content not in ctx:
                    ctx.append(content)
    return {"ctx_docs": ctx}

def finalize_node(state: AgentState):
    """Run safety validation on the last assistant text; decide send or escalate."""
    # Find the last assistant natural-language message (not a tool result)
    final_text = ""
    for m in reversed(state.get("messages", [])):
        if getattr(m, "type", "") == "ai" and getattr(m, "content", None):
            final_text = m.content
            break

    if not final_text:
        return {"decision": "escalate", "validation_reason": "empty_draft"}

    ctx_docs = state.get("ctx_docs", [])
    val = llm_validate(ctx_docs, final_text)

    return {
        "decision": "send" if val.get("is_valid") else "escalate",
        "validation_reason": val.get("reason", "")
    }

# ----------------------------
# Graph Wiring
# ----------------------------
graph = StateGraph(AgentState)

graph.add_node("agent", agent_node)
graph.add_node("tools", tools_node)
graph.add_node("collect_context", collect_context_node)
graph.add_node("finalize", finalize_node)

graph.set_entry_point("agent")

# If the assistant requested a tool, go run it; otherwise continue
graph.add_conditional_edges("agent", tools_condition)

# After a tool executes, collect context (if it was rag_search), then return to the agent
graph.add_edge("tools", "collect_context")
graph.add_edge("collect_context", "agent")

# When no more tools are requested, we are done planning → finalize/validate
graph.add_edge("agent", "finalize")

# Terminal branch
graph.add_conditional_edges(
    "finalize",
    lambda s: s.get("decision", "escalate"),
    {"send": END, "escalate": END}
)

app = graph.compile()

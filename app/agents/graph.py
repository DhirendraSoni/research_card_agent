import json
from typing import Dict, Any
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.language_models.chat_models import BaseChatModel

from .state import AgentState
from .policy import (
    INTENT_CLASSIFY_PROMPT, PLAN_PROMPT, THINK_PROMPT, DECIDE_PROMPT
)
from .tools import validate_card_ownership, cancel_card, dispatch_replacement, get_default_address

def _json_from_llm(llm: BaseChatModel, prompt: str) -> Dict[str, Any]:
    resp = llm.invoke(prompt)
    text = getattr(resp, "content", resp)  # ChatBedrock returns an AIMessage
    # Try to extract the JSON block
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        block = text[start:end]
        return json.loads(block)
    except Exception:
        return {}

def node_classify(state: AgentState, llm: BaseChatModel) -> AgentState:
    user_msg = state.get("user_query", "")
    parsed = _json_from_llm(llm, INTENT_CLASSIFY_PROMPT.format(user_message=user_msg))

    # Update fields if parsed
    for k in ["reason", "selected_card_id", "address"]:
        if parsed.get(k):
            state[k] = parsed[k]

    if parsed.get("address_confirmed") is not None:
        state["address_confirmed"] = bool(parsed["address_confirmed"])

    if parsed.get("delivery_confirmed") is not None:
        state["delivery_confirmed"] = bool(parsed["delivery_confirmed"])

    state["intent"] = parsed.get("intent", "other")
    state.setdefault("events", []).append(f"Intent classified: {state['intent']}")
    return state

def node_plan(state: AgentState, llm: BaseChatModel) -> AgentState:
    plan = llm.invoke(PLAN_PROMPT.format(
        selected_card_id=state.get("selected_card_id"),
        reason=state.get("reason"),
        address_confirmed=state.get("address_confirmed"),
        delivery_confirmed=state.get("delivery_confirmed"),
        address=state.get("address"),
    ))
    state["plan"] = getattr(plan, "content", str(plan))
    return state

def node_think(state: AgentState, llm: BaseChatModel) -> AgentState:
    thought = llm.invoke(THINK_PROMPT.format(
        intent=state.get("intent"),
        selected_card_id=state.get("selected_card_id"),
        reason=state.get("reason"),
        address=state.get("address"),
        address_confirmed=state.get("address_confirmed"),
        delivery_confirmed=state.get("delivery_confirmed"),
    ))
    t = getattr(thought, "content", str(thought))
    state["thoughts"] = (state.get("thoughts") or []) + [t]
    return state

def node_decide(state: AgentState, llm: BaseChatModel) -> AgentState:
    parsed = _json_from_llm(llm, DECIDE_PROMPT.format(
        intent=state.get("intent"),
        selected_card_id=state.get("selected_card_id"),
        reason=state.get("reason"),
        address=state.get("address"),
        address_confirmed=state.get("address_confirmed"),
        delivery_confirmed=state.get("delivery_confirmed"),
    ))
    state["decision"] = parsed.get("decision", "ask_user")
    state["next_questions"] = parsed.get("questions", [])
    state.setdefault("events", []).append(f"Decision: {state['decision']}")
    return state

def node_validate(state: AgentState) -> AgentState:
    ok, msg = validate_card_ownership(state.get("selected_card_id",""))
    state["ownership_validated"] = ok
    state.setdefault("events", []).append(msg)
    return state

def node_cancel_and_dispatch(state: AgentState) -> AgentState:
    cid = state.get("selected_card_id","")
    addr = state.get("address") or get_default_address()
    cancel_res = cancel_card(cid)
    dispatch_res = dispatch_replacement(cid, addr)
    state.setdefault("events", []).extend([cancel_res["event"], dispatch_res["event"]])
    state["final_message"] = (
        "Your card has been successfully cancelled and a new card is dispatched "
        "to the confirmed address."
    )
    return state

def build_graph(llm: BaseChatModel):
    g = StateGraph(AgentState)

    # Bind LLM into nodes via lambda closures
    g.add_node("classify", lambda s: node_classify(s, llm))
    g.add_node("plan_node", lambda s: node_plan(s, llm))
    g.add_node("think_node", lambda s: node_think(s, llm))
    g.add_node("decide_node", lambda s: node_decide(s, llm))


    g.add_node("validate", node_validate)
    g.add_node("cancel_dispatch", node_cancel_and_dispatch)

    # Edges
    g.add_edge(START, "classify")
    g.add_edge("classify", "plan_node")
    g.add_edge("plan_node", "think_node")
    g.add_edge("think_node", "decide_node")

    def route_from_decide(state: AgentState):
        return "validate" if state.get("decision") == "proceed_replacement" else END

    g.add_conditional_edges
    ("decide_node", route_from_decide,
        {"validate": "validate", 
         "END": END})

    g.add_edge("validate", "cancel_dispatch")
    g.add_edge("cancel_dispatch", END)

    return g.compile()

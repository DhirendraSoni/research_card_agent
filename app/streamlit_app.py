import os
import json
import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

# adjust imports as per your project structure
from agents.graph import build_graph
from agents.state import AgentState
from agents.tools import load_profile, get_default_address
from models.bedrock_llm import get_bedrock_llm

load_dotenv()
st.set_page_config(page_title="Card Replacement Autonomous Agent", page_icon="💳", layout="wide")

# ---------- Sidebar ----------
profile = load_profile()
st.sidebar.header("👤 User")
st.sidebar.write(f"**User ID:** `{profile.get('user_id', '-')}`")

cards = profile.get("cards", [])
if cards:
    st.sidebar.subheader("💼 Cards on file")
    st.sidebar.dataframe(
        { 
            "card_id":[c.get("card_id","") for c in cards],
            "type":[c.get("type","") for c in cards],
            "masked":[c.get("masked_number","") for c in cards],
            "status":[c.get("status","") for c in cards]
        },
        use_container_width=True
    )

st.sidebar.subheader("🏠 Default Address")
st.sidebar.caption(get_default_address())

debug = st.sidebar.toggle("Show raw agent internals", value=False)

# ---------- Session init ----------
if "graph" not in st.session_state:
    llm = get_bedrock_llm()
    st.session_state.graph = build_graph(llm)

if "state" not in st.session_state:
    st.session_state.state = AgentState(
        user_query="",
        messages=[],
        thoughts=[],
        events=[],
        address_confirmed=None,
        delivery_confirmed=None,
    )

# ---------- Main Layout ----------
st.title("💳 Card Replacement Autonomous Agent")
st.caption("Autonomous: plan → think → decide → act. I will ask for anything missing.")

# Chat input
with st.form("chat", border=False):
    user_msg = st.text_input(
        "Ask me to replace or cancel a card (e.g., 'Replace CRD-001 due to damage and ship to my saved address.')"
    )
    submit_chat = st.form_submit_button("Send")
    if submit_chat and user_msg.strip():
        st.session_state.state["user_query"] = user_msg.strip()
        st.session_state.state["messages"] = (
            st.session_state.state.get("messages") or []
        ) + [HumanMessage(content=user_msg.strip())]
        out = st.session_state.graph.invoke(st.session_state.state)
        for k, v in out.items():
            st.session_state.state[k] = v

# Transcript
for m in st.session_state.state.get("messages", []):
    if isinstance(m, HumanMessage):
        with st.chat_message("user"):
            st.write(m.content)
    elif isinstance(m, AIMessage):
        with st.chat_message("assistant"):
            st.write(m.content)

# Guided details form if something missing
qs = st.session_state.state.get("next_questions") or []
need_reason = not st.session_state.state.get("reason")
need_address = st.session_state.state.get("address_confirmed") is not True
need_delivery = st.session_state.state.get("delivery_confirmed") is not True
need_card = not st.session_state.state.get("selected_card_id")

if qs or need_reason or need_address or need_delivery or need_card:
    st.subheader("🔎 I need a few details")
    for q in qs:
        st.markdown(f"- {q}")

    with st.form("details_form", border=True):
        # Card
        if need_card:
            choices = [f"{c['card_id']} · {c['type']} ({c['masked_number']})" for c in cards]
            sel = st.selectbox("Select a card", choices)
            if sel:
                st.session_state.state["selected_card_id"] = sel.split(" · ")[0]

        # Reason
        if need_reason:
            reason = st.text_input("Reason for replacement")
            if reason:
                st.session_state.state["reason"] = reason

        # Address
        default_addr = get_default_address()
        st.caption(f"Saved address: {default_addr}")
        if need_address:
            addr_confirm = st.checkbox("Ship to saved address?")
            manual_addr = st.text_input("Or type a different delivery address")
            if addr_confirm and not manual_addr.strip():
                st.session_state.state["address"] = default_addr
                st.session_state.state["address_confirmed"] = True
            elif manual_addr.strip():
                st.session_state.state["address"] = manual_addr.strip()
                st.session_state.state["address_confirmed"] = True

        # Delivery confirm
        if need_delivery:
            deliver_ok = st.checkbox("Confirm dispatch to confirmed address")
            if deliver_ok:
                st.session_state.state["delivery_confirmed"] = True

        if st.form_submit_button("Continue"):
            st.session_state.state["user_query"] = "(user provided details)"
            out = st.session_state.graph.invoke(st.session_state.state)
            for k, v in out.items():
                st.session_state.state[k] = v
            st.experimental_rerun()

# --- Agent analysis on main page ---
st.subheader("🧠 Agent analysis")
if st.session_state.state.get("plan"):
    with st.expander("Plan", expanded=True):
        st.code(st.session_state.state["plan"])
if st.session_state.state.get("thoughts"):
    with st.expander("Think"):
        for i, t in enumerate(st.session_state.state["thoughts"], start=1):
            st.code(f"[{i}] {t}")
if st.session_state.state.get("events"):
    with st.expander("Events"):
        st.code("\n".join(st.session_state.state["events"]))

# --- Final success message ---
cid = st.session_state.state.get("selected_card_id")
reason = st.session_state.state.get("reason")
addr_ok = st.session_state.state.get("address_confirmed") is True
del_ok = st.session_state.state.get("delivery_confirmed") is True

if cid and reason and addr_ok and del_ok:
    st.success("✅ Card is successfully replaced and new card is dispatched on provided delivery address.")

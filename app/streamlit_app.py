import os
import json
import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

from agents.graph import build_graph
from agents.state import AgentState
from agents.tools import load_profile, get_default_address
from models.bedrock_llm import get_bedrock_llm

load_dotenv()

st.set_page_config(page_title="Card Replacement Autonomous Agent", page_icon="💳")
st.title("💳 Card Replacement Autonomous Agent")

# Sidebar: profile & cards
profile = load_profile()
st.sidebar.header("User Profile")
st.sidebar.write(f"**User ID:** {profile.get('user_id')}")

cards = profile.get("cards", [])
st.sidebar.subheader("Cards on file")
st.sidebar.table({ 
    "card_id":[c["card_id"] for c in cards],
    "type":[c["type"] for c in cards],
    "masked_number":[c["masked_number"] for c in cards],
    "status":[c["status"] for c in cards]
})

st.sidebar.subheader("Default Address")
st.sidebar.caption(get_default_address())

# Debug toggle
debug = st.sidebar.toggle("Show agent plan/think/events", value=os.getenv("AGENT_DEBUG","false").lower()=="true")

# Initialize session state
if "graph" not in st.session_state:
    try:
        llm = get_bedrock_llm()
    except Exception as e:
        st.error(f"LLM init failed: {e}")
        st.stop()
    st.session_state.graph = build_graph(llm)

if "state" not in st.session_state:
    st.session_state.state = AgentState(
        user_query="",
        messages=[],
        thoughts=[],
        events=[]
    )

# Chat UI
with st.form("chat"):
    user_msg = st.text_input("Type your request (e.g., 'Replace my Visa card 1234; deliver to my saved address.')")
    submitted = st.form_submit_button("Send")
    if submitted and user_msg.strip():
        st.session_state.state["user_query"] = user_msg.strip()
        st.session_state.state["messages"] = (st.session_state.state.get("messages") or []) + [HumanMessage(content=user_msg.strip())]

        # Run one pass
        out = st.session_state.graph.invoke(st.session_state.state)

        # Update state
        for k,v in out.items():
            st.session_state.state[k] = v

# Render chat & agent outputs
for m in st.session_state.state.get("messages", []):
    if isinstance(m, HumanMessage):
        with st.chat_message("user"):
            st.write(m.content)
    elif isinstance(m, AIMessage):
        with st.chat_message("assistant"):
            st.write(m.content)

# If the agent has questions
qs = st.session_state.state.get("next_questions") or []
if qs:
    with st.chat_message("assistant"):
        st.markdown("I need a couple of details before proceeding:")
        for q in qs:
            st.write("- " + q)

# If final message exists
if st.session_state.state.get("final_message"):
    with st.chat_message("assistant"):
        st.success(st.session_state.state["final_message"])

# Optional debug panel
if debug:
    st.divider()
    st.subheader("Agent Plan / Thoughts / Events")
    if st.session_state.state.get("plan"):
        st.markdown("**Plan:**")
        st.code(st.session_state.state["plan"])

    if st.session_state.state.get("thoughts"):
        st.markdown("**Think:**")
        for i, t in enumerate(st.session_state.state["thoughts"], start=1):
            st.code(f"[{i}] {t}")

    if st.session_state.state.get("events"):
        st.markdown("**Events:**")
        st.code("\n".join(st.session_state.state["events"]))

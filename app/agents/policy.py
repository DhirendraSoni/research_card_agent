# app/agents/policy.py

INTENT_CLASSIFY_PROMPT = """
You are an intent and information extractor for a credit card support agent.
Task: Given a user's message, classify intent and extract details.

Intents you may output (lowercase):
- replace_card
- cancel_card
- address_update
- status_check
- other

Also extract structured fields if present:
- selected_card_id
- reason
- address (full single-line string if the user provided or confirmed)
- address_confirmed (true/false)
- delivery_confirmed (true/false)

Return STRICT JSON with keys: intent, selected_card_id, reason, address, address_confirmed, delivery_confirmed.
If a field is unknown, return null. Example:
{{
 "intent": "replace_card",
 "selected_card_id": "CRD-001",
 "reason": "left mirror broken in accident",
 "address": null,
 "address_confirmed": null,
 "delivery_confirmed": null
}}
User message: {user_message}
"""

PLAN_PROMPT = """
Plan the steps for handling a card replacement request with the following constraints:
1) Ask for reason if missing.
2) Confirm or collect address if missing.
3) Confirm final delivery if missing.
4) Validate ownership.
5) Cancel the old card and dispatch a replacement.
Respond with a 3-6 bullet plan.
Context so far:
- selected_card_id: {selected_card_id}
- reason: {reason}
- address_confirmed: {address_confirmed}
- delivery_confirmed: {delivery_confirmed}
- address: {address}
"""

THINK_PROMPT = """
Think step: Given the current state, reflect on missing info and any potential risks.
Respond with 2-4 concise bullet points.
State:
- intent: {intent}
- selected_card_id: {selected_card_id}
- reason: {reason}
- address: {address}
- address_confirmed: {address_confirmed}
- delivery_confirmed: {delivery_confirmed}
"""

DECIDE_PROMPT = """
Decide what to do next. Required fields to proceed with replacement:
- intent in {{ "replace_card","cancel_card" }}
- selected_card_id
- reason
- address_confirmed is true AND address is set
- delivery_confirmed is true

If anything is missing, set decision = "ask_user" and produce the minimal list of questions to ask next
covering (a) reason, (b) address confirmation, (c) final delivery confirmation, and (d) card selection if multiple.

Output STRICT JSON:
{{
 "decision": "ask_user" | "proceed_replacement" | "exit",
 "questions": ["...","..."]  // empty if none
}}

State:
- intent: {intent}
- selected_card_id: {selected_card_id}
- reason: {reason}
- address: {address}
- address_confirmed: {address_confirmed}
- delivery_confirmed: {delivery_confirmed}
"""

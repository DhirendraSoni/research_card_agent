from typing import TypedDict, List, Optional, Literal
from langchain_core.messages import BaseMessage

class AgentState(TypedDict, total=False):
    # user input on each turn
    user_query: str

    # extracted/confirmed fields
    selected_card_id: Optional[str]
    reason: Optional[str]
    address_confirmed: Optional[bool]
    address: Optional[str]
    delivery_confirmed: Optional[bool]

    # agent cognitive trace
    plan: Optional[str]
    thoughts: List[str]
    decision: Optional[Literal["ask_user", "proceed_replacement", "exit"]]
    next_questions: List[str]

    # validations & side-effects
    ownership_validated: bool
    final_message: Optional[str]

    # misc
    messages: List[BaseMessage]
    events: List[str]

import json
import os
from typing import Dict, Any, Tuple

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "mock_cards.json")

def load_profile() -> Dict[str, Any]:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def validate_card_ownership(card_id: str) -> Tuple[bool, str]:
    profile = load_profile()
    ok = any(c["card_id"] == card_id for c in profile.get("cards", []))
    return ok, "Ownership validated." if ok else "Card not found for this user."

def cancel_card(card_id: str) -> Dict[str, Any]:
    # Mock cancellation
    return {"card_id": card_id, "status": "CANCELLED", "event": f"Card {card_id} cancelled."}

def dispatch_replacement(card_id: str, address: str) -> Dict[str, Any]:
    # Mock dispatch
    return {
        "card_id": card_id,
        "tracking_id": "TRK-" + card_id.replace("CRD",""),
        "address": address,
        "event": f"Replacement for {card_id} dispatched to: {address}"
    }

def get_default_address() -> str:
    profile = load_profile()
    addr = profile.get("address", {})
    return f"{addr.get('line1','')}, {addr.get('line2','')}, {addr.get('city','')}, {addr.get('state','')}-{addr.get('pincode','')}, {addr.get('country','')}".strip(", ")

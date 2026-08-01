import json
import os
import time
from typing import List, Dict

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "history_data.json")

def load_history() -> List[Dict]:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(history: List[Dict]):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Error saving history: {e}")

_history_store: List[Dict] = load_history()

def get_history() -> List[Dict]:
    return _history_store

def add_history_entry(entry: Dict) -> Dict:
    record = {
        "id": f"rec_{int(time.time() * 1000)}",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        **entry
    }
    # Keep last 100 records
    _history_store.insert(0, record)
    if len(_history_store) > 100:
        _history_store.pop()
    save_history(_history_store)
    return record

def clear_history():
    global _history_store
    _history_store = []
    save_history([])

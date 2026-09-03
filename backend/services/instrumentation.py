"""
Search Match & Satisfaction Instrumentation Service.
Logs user queries, matched product IDs, satisfaction scores, and match confidence modes
to disk (JSONL) and active DB to build labeled eval datasets over time.
"""
import os
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from models.db import MEM_DB, USE_IN_MEMORY, get_collection, save_mem_db

LOG_FILE = os.getenv("MATCH_EVAL_LOG_FILE", "match_eval_logs.jsonl")

def log_search_match(
    user_query: str,
    matched_product_id: str,
    satisfaction_score: float,
    match_score: float,
    mode: str,
    session_id: Optional[str] = None,
    product_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Logs a query-product match event for offline evaluation and continuous drift analysis.
    """
    log_id = str(uuid.uuid4())
    record = {
        "_id": log_id,
        "session_id": session_id or "",
        "timestamp": datetime.utcnow().isoformat(),
        "query": user_query,
        "matched_product_id": matched_product_id,
        "product_name": product_name or "",
        "satisfaction_score": float(satisfaction_score),
        "match_score": float(match_score),
        "match_mode": mode,
    }

    # 1. Append to local JSONL log file
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as e:
        pass

    # 2. Persist in database collection
    try:
        if USE_IN_MEMORY:
            if "match_logs" not in MEM_DB:
                MEM_DB["match_logs"] = {}
            MEM_DB["match_logs"][log_id] = record
            save_mem_db()
        else:
            get_collection("match_logs").insert_one(record)
    except Exception as e:
        pass

    return record

def export_eval_dataset(limit: int = 500) -> List[Dict[str, Any]]:
    """Exports the logged matches as a labeled eval dataset."""
    if USE_IN_MEMORY:
        logs = list(MEM_DB.get("match_logs", {}).values())
    else:
        logs = list(get_collection("match_logs").find({}).limit(limit))
    return logs

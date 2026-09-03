import logging
import datetime
from typing import Optional, Dict
from models.db import get_collection, USE_IN_MEMORY, MEM_DB, save_mem_db
from orchestration.state import ConversationAIState

logger = logging.getLogger("salesai.orchestration.state_repository")

# In-memory local cache for instant retrieval without IO overhead
_STATE_CACHE: Dict[str, ConversationAIState] = {}


class StateRepository:
    """
    Repository for persisting and retrieving canonical ConversationAIState per session_id.
    Synchronizes between instant in-memory cache and MongoDB / local JSON database.
    """

    @classmethod
    def get_collection(cls):
        return get_collection("conversation_states")

    @classmethod
    def load(cls, session_id: str) -> ConversationAIState:
        if not session_id:
            return ConversationAIState(session_id="anonymous")

        # 1. Check in-memory fast cache
        if session_id in _STATE_CACHE:
            return _STATE_CACHE[session_id]

        # 2. Check persistence DB
        data = None
        try:
            if USE_IN_MEMORY:
                if "conversation_states" not in MEM_DB:
                    MEM_DB["conversation_states"] = {}
                data = MEM_DB["conversation_states"].get(session_id)
            else:
                data = cls.get_collection().find_one({"_id": session_id})
        except Exception as e:
            logger.warning(f"Error loading state for session {session_id} from DB: {e}")

        if data:
            if "_id" in data and "session_id" not in data:
                data["session_id"] = data["_id"]
            state = ConversationAIState.from_dict(data)
        else:
            state = ConversationAIState(session_id=session_id)

        _STATE_CACHE[session_id] = state
        return state

    @classmethod
    def save(cls, state: ConversationAIState) -> None:
        if not state or not state.session_id:
            return

        state.updated_at = datetime.datetime.utcnow().isoformat()
        _STATE_CACHE[state.session_id] = state

        doc = state.to_dict()
        doc["_id"] = state.session_id

        try:
            if USE_IN_MEMORY:
                if "conversation_states" not in MEM_DB:
                    MEM_DB["conversation_states"] = {}
                MEM_DB["conversation_states"][state.session_id] = doc
                save_mem_db()
            else:
                cls.get_collection().update_one(
                    {"_id": state.session_id},
                    {"$set": doc},
                    upsert=True
                )
        except Exception as e:
            logger.error(f"Failed to persist state for session {state.session_id}: {e}")

    @classmethod
    def clear_cache(cls) -> None:
        """Utility for test suites to reset memory cache."""
        _STATE_CACHE.clear()

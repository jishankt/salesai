from datetime import datetime

from models.db import MEM_DB, USE_IN_MEMORY, get_collection, save_mem_db


class ChatSession:
    @classmethod
    def get_collection(cls):
        return get_collection("chat_sessions")

    @classmethod
    def get_all(cls):
        if USE_IN_MEMORY:
            return list(MEM_DB.get("chat_sessions", {}).values())
        return list(cls.get_collection().find({}))

    @classmethod
    def get_or_create(cls, session_id):
        if USE_IN_MEMORY:
            session = MEM_DB["chat_sessions"].get(session_id)
            if not session:
                session = {"_id": session_id, "messages": [], "created_at": datetime.utcnow()}
                MEM_DB["chat_sessions"][session_id] = session
                save_mem_db()
            return session

        session = cls.get_collection().find_one({"_id": session_id})
        if not session:
            session = {"_id": session_id, "messages": [], "created_at": datetime.utcnow()}
            cls.get_collection().insert_one(session)
        return session

    @classmethod
    def add_message(cls, session_id, role, content, **kwargs):
        msg = {"role": role, "content": content, "timestamp": datetime.utcnow().isoformat() + "Z"}
        msg.update(kwargs)

        if USE_IN_MEMORY:
            session = cls.get_or_create(session_id)
            session["messages"].append(msg)
            save_mem_db()
            return

        cls.get_collection().update_one({"_id": session_id}, {"$push": {"messages": msg}})

    @classmethod
    def pop_last_message(cls, session_id):
        if USE_IN_MEMORY:
            session = cls.get_or_create(session_id)
            if session["messages"]:
                session["messages"].pop()
                save_mem_db()
            return
        cls.get_collection().update_one({"_id": session_id}, {"$pop": {"messages": 1}})

    @classmethod
    def update_last_assistant_message(cls, session_id, content):
        return cls.update_last_assistant_message_content_and_translation(session_id, content)

    @classmethod
    def update_last_assistant_message_content_and_translation(cls, session_id, content, original_content=None):
        session = cls.get_or_create(session_id)
        for idx in range(len(session.get("messages", [])) - 1, -1, -1):
            msg = session["messages"][idx]
            if msg.get("role") == "assistant":
                msg["content"] = content
                if original_content:
                    msg["original_content"] = original_content
                if USE_IN_MEMORY:
                    save_mem_db()
                else:
                    update_dict = {f"messages.{idx}.content": content}
                    if original_content:
                        update_dict[f"messages.{idx}.original_content"] = original_content
                    cls.get_collection().update_one({"_id": session_id}, {"$set": update_dict})
                return True
        return False

import uuid
from datetime import datetime

from models.db import MEM_DB, USE_IN_MEMORY, get_collection, save_mem_db


class Lead:
    @classmethod
    def get_collection(cls):
        return get_collection("leads")

    @classmethod
    def create_or_update_lead(cls, session_id, name=None, contact=None, needs=None, budget=None, source=None, status=None, territory=None):
        if USE_IN_MEMORY:
            lead = MEM_DB["leads"].get(session_id)
            if not lead:
                lead = {
                    "_id": str(uuid.uuid4()),
                    "session_id": session_id,
                    "status": "new",
                    "score": 0,
                    "score_actions": [],
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
                MEM_DB["leads"][session_id] = lead

            if name:
                lead["name"] = name
            if contact:
                lead["contact"] = contact
            if needs:
                lead["needs"] = needs
            if budget:
                lead["budget"] = budget
            if source:
                lead["source"] = source
            if status:
                lead["status"] = status
            if territory:
                lead["territory"] = territory
            lead["updated_at"] = datetime.utcnow()

            # Auto-promote new/prospect status to qualified if name and contact are both populated
            if lead.get("name") and lead.get("contact") and lead.get("status") in ("new", "prospect"):
                lead["status"] = "qualified"

            save_mem_db()
            return lead

        query = {"session_id": session_id}
        update = {"$set": {"updated_at": datetime.utcnow()}}
        if name:
            update["$set"]["name"] = name
        if contact:
            update["$set"]["contact"] = contact
        if needs:
            update["$set"]["needs"] = needs
        if budget:
            update["$set"]["budget"] = budget
        if source:
            update["$set"]["source"] = source
        if status:
            update["$set"]["status"] = status
        if territory:
            update["$set"]["territory"] = territory

        existing = cls.get_collection().find_one(query)
        if not existing:
            update["$setOnInsert"] = {
                "_id": str(uuid.uuid4()),
                "session_id": session_id,
                "status": status or "new",
                "score": 0,
                "score_actions": [],
                "created_at": datetime.utcnow(),
            }
        else:
            has_name = name or existing.get("name")
            has_contact = contact or existing.get("contact")
            current_status = status or existing.get("status", "new")
            if has_name and has_contact and current_status in ("new", "prospect"):
                update["$set"]["status"] = "qualified"

        cls.get_collection().update_one(query, update, upsert=True)
        return cls.get_collection().find_one(query)

    @classmethod
    def increment_score(cls, session_id, points, action_name):
        if USE_IN_MEMORY:
            # Ensure lead exists first
            lead = cls.create_or_update_lead(session_id)
            if "score" not in lead:
                lead["score"] = 0
            if "score_actions" not in lead:
                lead["score_actions"] = []
            
            if action_name not in lead["score_actions"]:
                lead["score"] += points
                lead["score_actions"].append(action_name)
                save_mem_db()
            return lead
            
        # Ensure lead exists
        cls.create_or_update_lead(session_id)
        query = {"session_id": session_id}
        existing = cls.get_collection().find_one(query)
        if existing:
            score_actions = existing.get("score_actions", [])
            if action_name not in score_actions:
                cls.get_collection().update_one(
                    query,
                    {
                        "$inc": {"score": points},
                        "$push": {"score_actions": action_name},
                        "$set": {"updated_at": datetime.utcnow()}
                    }
                )
        return cls.get_collection().find_one(query)

    @classmethod
    def get_by_session(cls, session_id):
        if USE_IN_MEMORY:
            return MEM_DB["leads"].get(session_id)
        return cls.get_collection().find_one({"session_id": session_id})

    @classmethod
    def set_status(cls, session_id, status, extra=None):
        extra = extra or {}
        if USE_IN_MEMORY:
            lead = MEM_DB["leads"].get(session_id)
            if lead:
                lead["status"] = status
                lead.update(extra)
                save_mem_db()
            return
        cls.get_collection().update_one(
            {"session_id": session_id},
            {"$set": {"status": status, **extra}},
            upsert=True,
        )

    @classmethod
    def get_all(cls):
        if USE_IN_MEMORY:
            result = []
            for l in MEM_DB["leads"].values():
                safe = dict(l)
                for k in ("created_at", "updated_at"):
                    if isinstance(safe.get(k), datetime):
                        safe[k] = safe[k].isoformat() + "Z"
                    elif isinstance(safe.get(k), str) and not safe[k].endswith("Z"):
                        safe[k] += "Z"
                result.append(safe)
            return result
        return list(cls.get_collection().find({}))

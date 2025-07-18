import os
import json
from cryptography.fernet import Fernet, InvalidToken
from datetime import datetime, date
from uuid import UUID
from typing import Dict, Any, List

FERNET_KEY = os.getenv("ENCRYPTION_KEY")
if not FERNET_KEY:
    raise RuntimeError("ENCRYPTION_KEY is not set in the environment variables.")
fernet = Fernet(FERNET_KEY.encode() if isinstance(FERNET_KEY, str) else FERNET_KEY)

# Required fields for each model
REQUIRED_FIELDS = {
    "rock": [
        "id", "rock_id", "rock_name", "smart_objective", "quarter_id", "assigned_to_id", "assigned_to_name", "created_at", "updated_at"
    ],
    "task": [
        "id", "rock_id", "week", "task_id", "task", "sub_tasks", "comments", "created_at", "updated_at"
    ],
    "todo": [
        "id", "todo_id", "task_title", "assigned_to", "designation", "due_date", "linked_issue", "status", "quarter_id", "assigned_to_id", "created_at", "updated_at"
    ],
    "issue": [
        "id", "issue_id", "issue_title", "description", "raised_by", "discussion_notes", "linked_solution_type", "linked_solution_ref", "status", "quarter_id", "raised_by_id", "created_at", "updated_at"
    ],
    "quarter": [
        "id", "quarter", "weeks", "year", "title", "description", "participants", "status", "created_at", "updated_at"
    ]
}

def _serialize_excluded(fields: Dict[str, Any]) -> Dict[str, Any]:
    # Convert UUID, datetime, and date fields to string for storage
    result = {}
    for k, v in fields.items():
        if isinstance(v, UUID):
            result[k] = str(v)
        elif isinstance(v, list) and v and isinstance(v[0], UUID):
            result[k] = [str(x) for x in v]
        elif isinstance(v, datetime):
            result[k] = v.isoformat()
        elif isinstance(v, date):
            result[k] = v.isoformat()
        else:
            result[k] = v
    return result

def _deserialize_excluded(fields: Dict[str, Any], types: Dict[str, Any]) -> Dict[str, Any]:
    # Convert string fields back to UUID/datetime as needed
    result = {}
    for k, v in fields.items():
        typ = types.get(k)
        if typ == UUID:
            if isinstance(v, str) and v.strip():
                # Only convert non-empty strings to UUID
                try:
                    result[k] = UUID(v)
                except ValueError:
                    # Invalid UUID string, set to None
                    result[k] = None
            else:
                # Convert empty strings or other invalid values to None
                result[k] = None
        elif typ == List[UUID]:
            if isinstance(v, list):
                result[k] = [UUID(x) if isinstance(x, str) and x.strip() else None for x in v]
            else:
                result[k] = v
        elif typ == datetime:
            if isinstance(v, str) and v.strip():
                try:
                    result[k] = datetime.fromisoformat(v)
                except ValueError:
                    # Invalid datetime string, set to None
                    result[k] = None
            elif isinstance(v, datetime):
                result[k] = v  # Already a datetime object
            else:
                result[k] = None
        else:
            result[k] = v
    return result

def encrypt_dict(data: Dict[str, Any], exclude_fields: List[str]) -> Dict[str, Any]:
    # Split out excluded fields
    excluded = {k: data.pop(k) for k in exclude_fields if k in data}
    
    # Serialize date/datetime objects in the data to be encrypted
    serialized_data = {}
    for k, v in data.items():
        if isinstance(v, UUID):
            serialized_data[k] = str(v)
        elif isinstance(v, datetime):
            serialized_data[k] = v.isoformat()
        elif isinstance(v, date):
            serialized_data[k] = v.isoformat()
        else:
            serialized_data[k] = v
    
    encrypted_blob = fernet.encrypt(json.dumps(serialized_data).encode()).decode()
    return {
        **_serialize_excluded(excluded),
        "data_enc": encrypted_blob
    }

def decrypt_dict(db_data: Dict[str, Any], exclude_fields: List[str], exclude_types: Dict[str, Any]) -> Dict[str, Any]:
    # Extract excluded fields
    excluded = {k: db_data[k] for k in exclude_fields if k in db_data}
    decrypted_json = fernet.decrypt(db_data["data_enc"].encode()).decode()
    decrypted = json.loads(decrypted_json)
    # Convert excluded fields back to correct types
    excluded = _deserialize_excluded(excluded, exclude_types)
    return {**decrypted, **excluded}

def fill_required_fields(data: Dict[str, Any], model_name: str) -> Dict[str, Any]:
    """Ensure all required fields for the given model are present in the dict."""
    required = REQUIRED_FIELDS.get(model_name, [])
    for field in required:
        if field not in data:
            data[field] = None
    return data 
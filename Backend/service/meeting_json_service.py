"""
meeting_json_service.py is the ONLY source of truth for context (raw, structured, csv) storage and retrieval in MongoDB. All vector DB (Qdrant) indexing must be triggered from the route after saving. No circular imports.
"""
import json
from typing import Optional, Dict, List
from .db import db
from uuid import uuid4
from datetime import datetime
from utils.secure_fields import encrypt_dict, decrypt_dict


RAW_CONTEXT_COLLECTION = 'raw_contexts'
STRUCTURED_CONTEXT_COLLECTION = 'structured_contexts'


# Helper: ensure each context file has a unique id ("context_id") and an index ("context_index")
from uuid import uuid4
def ensure_context_id_and_index(doc, context_type, facilitator_id):
    changed = False
    if doc is None:
        return None
    if 'context_id' not in doc:
        doc['context_id'] = str(uuid4())
        changed = True
    if 'context_index' not in doc:
        # Use 0 for now, or could be incremented if you support multiple per facilitator
        doc['context_index'] = 0
        changed = True
    if changed:
        db[{
            'raw': RAW_CONTEXT_COLLECTION,
            'structured': STRUCTURED_CONTEXT_COLLECTION
        }[context_type]].replace_one({'facilitator_id': facilitator_id}, {'facilitator_id': facilitator_id, 'context': doc['context'], 'context_id': doc['context_id'], 'context_index': doc['context_index']}, upsert=True)
    return doc

# --- RAW CONTEXT ENCRYPTION ---
EXCLUDE_FIELDS = ["facilitator_id"]
EXCLUDE_TYPES = {"facilitator_id": str}

def safe_decrypt_raw_context(doc):
    if doc is None:
        return None
    if "data_enc" in doc:
        # Decrypt and merge with facilitator_id
        data = decrypt_dict(doc, EXCLUDE_FIELDS, EXCLUDE_TYPES)
        return data["context"] if "context" in data else data
    else:
        return doc["context"] if "context" in doc else doc

# Store raw context JSON in MongoDB
def save_raw_context_json(file, facilitator_id):
    content = file.file.read()
    try:
        # Handle different input types
        if isinstance(content, bytes):
            # Try to decode as UTF-8 first
            try:
                content = content.decode('utf-8')
            except UnicodeDecodeError:
                # If it fails, it might be already parsed content passed as bytes
                # Try to load it as JSON bytes directly
                import chardet
                encoding = chardet.detect(content)['encoding']
                if encoding:
                    content = content.decode(encoding)
                else:
                    raise ValueError("Could not detect file encoding")
        
        # Parse JSON
        if isinstance(content, str):
            json_data = json.loads(content)
        else:
            json_data = content  # Already parsed content
            
    except Exception as e:
        print("[ERROR] Failed to parse uploaded content:", e)
        raise
    print("[DEBUG] Uploaded raw context JSON:", json_data)
    # Encrypt all except facilitator_id
    to_encrypt = {"context": json_data}
    encrypted = encrypt_dict({**to_encrypt, "facilitator_id": facilitator_id}, EXCLUDE_FIELDS)
    db[RAW_CONTEXT_COLLECTION].replace_one({'facilitator_id': facilitator_id}, encrypted, upsert=True)
    return json_data

# Store structured context JSON in MongoDB
def save_structured_context_json(file, facilitator_id):
    content = file.file.read()
    json_data = json.loads(content)
    # Encrypt all except facilitator_id
    to_encrypt = {"context": json_data}
    encrypted = encrypt_dict({**to_encrypt, "facilitator_id": facilitator_id}, ["facilitator_id"])
    db[STRUCTURED_CONTEXT_COLLECTION].replace_one({'facilitator_id': facilitator_id}, encrypted, upsert=True)
    return json_data





# Retrieve raw context JSON for facilitator

def get_raw_context_json(facilitator_id, with_meta=False):
    doc = db[RAW_CONTEXT_COLLECTION].find_one({'facilitator_id': facilitator_id})
    doc = ensure_context_id_and_index(doc, 'raw', facilitator_id)
    if with_meta:
        return doc
    return safe_decrypt_raw_context(doc)

# Retrieve structured context JSON for facilitator

def get_structured_context_json(facilitator_id, with_meta=False):
    doc = db[STRUCTURED_CONTEXT_COLLECTION].find_one({'facilitator_id': facilitator_id})
    doc = ensure_context_id_and_index(doc, 'structured', facilitator_id)
    if with_meta:
        return doc
    return doc['context'] if doc else None

# Retrieve CSV context for facilitator



# ------------------- FINE-GRAINED CRUD (IN-FILE) -------------------

# -------- RAW JSON: CRUD for transcript segments (assume list at context['segments']) --------

def list_raw_segments(facilitator_id):
    """List all transcript segments for the facilitator's raw context. Each segment has a unique 'id'."""
    context = get_raw_context_json(facilitator_id)
    segments = context.get('segments', []) if context else []
    # Add IDs to legacy segments if missing
    changed = False
    for seg in segments:
        if 'id' not in seg:
            seg['id'] = str(uuid4())
            changed = True
    if changed:
        context['segments'] = segments
        db[RAW_CONTEXT_COLLECTION].replace_one({'facilitator_id': facilitator_id}, {'facilitator_id': facilitator_id, 'context': context}, upsert=True)
    return segments


def get_raw_segment(facilitator_id, segment_id):
    """Get a single transcript segment by unique ID."""
    segments = list_raw_segments(facilitator_id)
    for seg in segments:
        if seg.get('id') == segment_id:
            return seg
    return None


def create_raw_segment(facilitator_id, segment):
    """Append a new transcript segment with a unique ID."""
    context = get_raw_context_json(facilitator_id) or {}
    segments = context.get('segments', [])
    segment = dict(segment)
    segment['id'] = str(uuid4())
    segments.append(segment)
    context['segments'] = segments
    db[RAW_CONTEXT_COLLECTION].replace_one({'facilitator_id': facilitator_id}, {'facilitator_id': facilitator_id, 'context': context}, upsert=True)
    return segment


def update_raw_segment(facilitator_id, segment_id, segment):
    """Update a transcript segment by unique ID."""
    context = get_raw_context_json(facilitator_id)
    if not context or 'segments' not in context:
        return None
    segments = context['segments']
    for idx, seg in enumerate(segments):
        if seg.get('id') == segment_id:
            segment = dict(segment)
            segment['id'] = segment_id
            segments[idx] = segment
            context['segments'] = segments
            db[RAW_CONTEXT_COLLECTION].replace_one({'facilitator_id': facilitator_id}, {'facilitator_id': facilitator_id, 'context': context}, upsert=True)
            return segment
    return None


def delete_raw_segment(facilitator_id, segment_id):
    """Delete a transcript segment by unique ID."""
    context = get_raw_context_json(facilitator_id)
    if not context or 'segments' not in context:
        return False
    segments = context['segments']
    for idx, seg in enumerate(segments):
        if seg.get('id') == segment_id:
            removed = segments.pop(idx)
            context['segments'] = segments
            db[RAW_CONTEXT_COLLECTION].replace_one({'facilitator_id': facilitator_id}, {'facilitator_id': facilitator_id, 'context': context}, upsert=True)
            return removed
    return False

# -------- STRUCTURED JSON: CRUD for items by key (e.g., tasks, objectives, rocks) --------

def list_structured_items(facilitator_id, key):
    """List all items for a given key (e.g., 'tasks') in structured context. Each item has a unique 'id'."""
    context = get_structured_context_json(facilitator_id)
    items = context.get(key, []) if context else []
    changed = False
    for item in items:
        if 'id' not in item:
            item['id'] = str(uuid4())
            changed = True
    if changed:
        context[key] = items
        db[STRUCTURED_CONTEXT_COLLECTION].replace_one({'facilitator_id': facilitator_id}, {'facilitator_id': facilitator_id, 'context': context}, upsert=True)
    return items


def get_structured_item(facilitator_id, key, item_id):
    """Get a single item by unique ID for a given key in structured context."""
    items = list_structured_items(facilitator_id, key)
    for item in items:
        if item.get('id') == item_id:
            return item
    return None


def create_structured_item(facilitator_id, key, item):
    """Append a new item with a unique ID to a given key in structured context."""
    context = get_structured_context_json(facilitator_id) or {}
    items = context.get(key, [])
    item = dict(item)
    item['id'] = str(uuid4())
    items.append(item)
    context[key] = items
    db[STRUCTURED_CONTEXT_COLLECTION].replace_one({'facilitator_id': facilitator_id}, {'facilitator_id': facilitator_id, 'context': context}, upsert=True)
    return item


def update_structured_item(facilitator_id, key, item_id, item):
    """Update an item by unique ID for a given key in structured context."""
    context = get_structured_context_json(facilitator_id)
    if not context or key not in context:
        return None
    items = context[key]
    for idx, itm in enumerate(items):
        if itm.get('id') == item_id:
            item = dict(item)
            item['id'] = item_id
            items[idx] = item
            context[key] = items
            db[STRUCTURED_CONTEXT_COLLECTION].replace_one({'facilitator_id': facilitator_id}, {'facilitator_id': facilitator_id, 'context': context}, upsert=True)
            return item
    return None


def delete_structured_item(facilitator_id, key, item_id):
    """Delete an item by unique ID for a given key in structured context."""
    context = get_structured_context_json(facilitator_id)
    if not context or key not in context:
        return False
    items = context[key]
    for idx, itm in enumerate(items):
        if itm.get('id') == item_id:
            removed = items.pop(idx)
            context[key] = items
            db[STRUCTURED_CONTEXT_COLLECTION].replace_one({'facilitator_id': facilitator_id}, {'facilitator_id': facilitator_id, 'context': context}, upsert=True)
            return removed
    return False

# -------- CSV: CRUD for individual rows (list of dicts) --------

def list_csv_rows(facilitator_id):
    """(Deprecated) List all rows in the facilitator's CSV context. No longer used."""
    return []


def get_csv_row(facilitator_id, row_id):
    """(Deprecated) Get a single row by unique ID from CSV context. No longer used."""
    return None


def create_csv_row(facilitator_id, row):
    """(Deprecated) Append a new row with a unique ID to CSV context. No longer used."""
    return None


def update_csv_row(facilitator_id, row_id, row):
    """(Deprecated) Update a row by unique ID in CSV context. No longer used."""
    return None


def delete_csv_row(facilitator_id, row_id):
    """(Deprecated) Delete a row by unique ID in CSV context. No longer used."""
    return False

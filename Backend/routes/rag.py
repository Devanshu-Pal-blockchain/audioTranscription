from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
import os
from dotenv import load_dotenv

from service.meeting_json_service import (
    save_raw_context_json, save_structured_context_json, save_csv_context,
    get_raw_context_json, get_structured_context_json, get_csv_context,
    list_raw_segments, get_raw_segment, create_raw_segment, update_raw_segment, delete_raw_segment,
    list_structured_items, get_structured_item, create_structured_item, update_structured_item, delete_structured_item,
    list_csv_rows, get_csv_row, create_csv_row, update_csv_row, delete_csv_row
)

router = APIRouter()

from service.rag_vector_service import index_json_chunks, index_csv_chunks

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
# RAG+LLM answer endpoint (admin only)
###############################################################
# FINE-GRAINED CRUD ENDPOINTS FOR IN-FILE ITEMS (ID-BASED)
###############################################################

# -------- RAW JSON SEGMENTS --------
@router.get("/raw-segments")
async def api_list_raw_segments(token: str = Depends(oauth2_scheme)):
    admin_id = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])["sub"]
    return list_raw_segments(admin_id)

@router.get("/raw-segments/{segment_id}")
async def api_get_raw_segment(segment_id: str, token: str = Depends(oauth2_scheme)):
    admin_id = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])["sub"]
    seg = get_raw_segment(admin_id, segment_id)
    if not seg:
        raise HTTPException(404, "Segment not found")
    return seg

@router.post("/raw-segments")
async def api_create_raw_segment(segment: dict = Body(...), token: str = Depends(oauth2_scheme)):
    admin_id = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])["sub"]
    seg = create_raw_segment(admin_id, segment)
    # Re-index Qdrant
    from service.rag_vector_service import index_json_chunks
    json_data = get_raw_context_json(admin_id)
    index_json_chunks(json_data, collection_name=f"raw_{admin_id}")
    return seg

@router.put("/raw-segments/{segment_id}")
async def api_update_raw_segment(segment_id: str, segment: dict = Body(...), token: str = Depends(oauth2_scheme)):
    admin_id = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])["sub"]
    seg = update_raw_segment(admin_id, segment_id, segment)
    if not seg:
        raise HTTPException(404, "Segment not found")
    from service.rag_vector_service import index_json_chunks
    json_data = get_raw_context_json(admin_id)
    index_json_chunks(json_data, collection_name=f"raw_{admin_id}")
    return seg

@router.delete("/raw-segments/{segment_id}")
async def api_delete_raw_segment(segment_id: str, token: str = Depends(oauth2_scheme)):
    admin_id = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])["sub"]
    removed = delete_raw_segment(admin_id, segment_id)
    if not removed:
        raise HTTPException(404, "Segment not found")
    from service.rag_vector_service import index_json_chunks
    json_data = get_raw_context_json(admin_id)
    index_json_chunks(json_data, collection_name=f"raw_{admin_id}")
    return removed

# -------- STRUCTURED JSON ITEMS (by key) --------
@router.get("/structured-items/{key}")
async def api_list_structured_items(key: str, token: str = Depends(oauth2_scheme)):
    admin_id = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])["sub"]
    return list_structured_items(admin_id, key)

@router.get("/structured-items/{key}/{item_id}")
async def api_get_structured_item(key: str, item_id: str, token: str = Depends(oauth2_scheme)):
    admin_id = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])["sub"]
    item = get_structured_item(admin_id, key, item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    return item

@router.post("/structured-items/{key}")
async def api_create_structured_item(key: str, item: dict = Body(...), token: str = Depends(oauth2_scheme)):
    admin_id = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])["sub"]
    itm = create_structured_item(admin_id, key, item)
    from service.rag_vector_service import index_json_chunks
    json_data = get_structured_context_json(admin_id)
    index_json_chunks(json_data, collection_name=f"structured_{admin_id}")
    return itm

@router.put("/structured-items/{key}/{item_id}")
async def api_update_structured_item(key: str, item_id: str, item: dict = Body(...), token: str = Depends(oauth2_scheme)):
    admin_id = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])["sub"]
    itm = update_structured_item(admin_id, key, item_id, item)
    if not itm:
        raise HTTPException(404, "Item not found")
    from service.rag_vector_service import index_json_chunks
    json_data = get_structured_context_json(admin_id)
    index_json_chunks(json_data, collection_name=f"structured_{admin_id}")
    return itm

@router.delete("/structured-items/{key}/{item_id}")
async def api_delete_structured_item(key: str, item_id: str, token: str = Depends(oauth2_scheme)):
    admin_id = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])["sub"]
    removed = delete_structured_item(admin_id, key, item_id)
    if not removed:
        raise HTTPException(404, "Item not found")
    from service.rag_vector_service import index_json_chunks
    json_data = get_structured_context_json(admin_id)
    index_json_chunks(json_data, collection_name=f"structured_{admin_id}")
    return removed

# -------- CSV ROWS --------
@router.get("/csv-rows")
async def api_list_csv_rows(token: str = Depends(oauth2_scheme)):
    admin_id = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])["sub"]
    return list_csv_rows(admin_id)

@router.get("/csv-rows/{row_id}")
async def api_get_csv_row(row_id: str, token: str = Depends(oauth2_scheme)):
    admin_id = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])["sub"]
    row = get_csv_row(admin_id, row_id)
    if not row:
        raise HTTPException(404, "Row not found")
    return row

@router.post("/csv-rows")
async def api_create_csv_row(row: dict = Body(...), token: str = Depends(oauth2_scheme)):
    admin_id = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])["sub"]
    r = create_csv_row(admin_id, row)
    from service.rag_vector_service import index_csv_chunks
    csv_data = get_csv_context(admin_id)
    index_csv_chunks(csv_data, collection_name=f"csv_{admin_id}")
    return r

@router.put("/csv-rows/{row_id}")
async def api_update_csv_row(row_id: str, row: dict = Body(...), token: str = Depends(oauth2_scheme)):
    admin_id = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])["sub"]
    r = update_csv_row(admin_id, row_id, row)
    if not r:
        raise HTTPException(404, "Row not found")
    from service.rag_vector_service import index_csv_chunks
    csv_data = get_csv_context(admin_id)
    index_csv_chunks(csv_data, collection_name=f"csv_{admin_id}")
    return r

@router.delete("/csv-rows/{row_id}")
async def api_delete_csv_row(row_id: str, token: str = Depends(oauth2_scheme)):
    admin_id = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])["sub"]
    removed = delete_csv_row(admin_id, row_id)
    if not removed:
        raise HTTPException(404, "Row not found")
    from service.rag_vector_service import index_csv_chunks
    csv_data = get_csv_context(admin_id)
    index_csv_chunks(csv_data, collection_name=f"csv_{admin_id}")
    return removed
from service.rag_vector_service import rag_llm_answer

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

router = APIRouter()

# Dependency to check admin role
async def admin_required(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        role = payload.get("role")
        if role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins only.")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")


# Upload raw context JSON (admin only)

from service.rag_vector_service import index_json_chunks, index_csv_chunks

# Upload raw context JSON (admin only)
@router.post("/upload-raw-context")
async def upload_raw_context(file: UploadFile = File(...), token: str = Depends(oauth2_scheme)):
    print("[DEBUG] upload_raw_context called, file:", file)
    try:
        # Defensive: Check file
        if not file or not hasattr(file, 'filename') or not file.filename:
            print("[ERROR] No file uploaded or file is undefined.")
            raise HTTPException(status_code=400, detail="No file uploaded or file is undefined.")
        if not file.filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="Only JSON files are allowed.")

        # Defensive: Check and extract JWT token
        if not token or not isinstance(token, str):
            print("[ERROR] No token provided or token is not a string.")
            raise HTTPException(status_code=401, detail="No token provided.")
        if token.count('.') != 2:
            print(f"[ERROR] Malformed JWT token: {token}")
            raise HTTPException(status_code=401, detail="Malformed JWT token.")
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except JWTError as e:
            print(f"[ERROR] JWT decode failed: {e}")
            raise HTTPException(status_code=401, detail="Invalid JWT token.")
        admin_id = payload.get("sub")
        print("[DEBUG] About to read and parse file")
        json_data = save_raw_context_json(file, admin_id)
        print("[DEBUG] JSON received in endpoint:", json_data)
        # Accept both 'transcribed_segments' and 'transcribedSegments' (case-insensitive)
        segments = None
        for k in json_data.keys():
            if k.lower() == "transcribed_segments":
                segments = json_data[k]
                break
        print("[DEBUG] Segments extracted:", segments)
        if not isinstance(segments, list) or len(segments) == 0:
            print("[ERROR] Segments missing or empty! Parsed JSON:", json_data)
            raise HTTPException(status_code=400, detail={"error": "Raw context JSON must contain a non-empty 'transcribed_segments' list.", "parsed_json": json_data})
        valid_segments = [seg for seg in segments if isinstance(seg, dict) and seg.get("text") and isinstance(seg["text"], str) and seg["text"].strip()]
        print("[DEBUG] Valid segments:", valid_segments)
        if not valid_segments:
            print("[ERROR] No valid segments with non-empty text! Parsed JSON:", json_data)
            raise HTTPException(status_code=400, detail={"error": "Each segment in 'transcribed_segments' must have a non-empty 'text' field.", "parsed_json": json_data})
        from service.rag_vector_service import index_json_chunks
        try:
            index_json_chunks(json_data, collection_name=f"raw_{admin_id}", context_type="raw")
        except Exception as e:
            import traceback
            print("[ERROR] Failed to index raw context in Qdrant:", e)
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Failed to index raw context: {str(e)}")
        print("[DEBUG] Upload and indexing successful!")
        return {"message": f"Raw context JSON '{file.filename}' uploaded, stored, and indexed."}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print("[FATAL ERROR] Exception in upload_raw_context:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Fatal error in upload_raw_context: {str(e)}")

# Upload structured context JSON (admin only)

# Upload structured context JSON (admin only)
@router.post("/upload-structured-context")
async def upload_structured_context(file: UploadFile = File(...), token: str = Depends(oauth2_scheme)):
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="Only JSON files are allowed.")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        admin_id = payload.get("sub")
        json_data = save_structured_context_json(file, admin_id)
        index_json_chunks(json_data, collection_name=f"structured_{admin_id}")
        return {"message": f"Structured context JSON '{file.filename}' uploaded, stored, and indexed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Upload CSV context (admin only)

# Upload CSV context (admin only)
@router.post("/upload-csv-context")
async def upload_csv_context(file: UploadFile = File(...), token: str = Depends(oauth2_scheme)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        admin_id = payload.get("sub")
        csv_data = save_csv_context(file, admin_id)
        index_csv_chunks(csv_data, collection_name=f"csv_{admin_id}")
        return {"message": f"CSV context '{file.filename}' uploaded, stored, and indexed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# CRUD endpoints for context management (admin only)
@router.get("/contexts")
async def list_contexts(token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    admin_id = payload.get("sub")
    raw = get_raw_context_json(admin_id)
    structured = get_structured_context_json(admin_id)
    csv_ctx = get_csv_context(admin_id)
    return {"raw": bool(raw), "structured": bool(structured), "csv": bool(csv_ctx)}

@router.get("/context/{context_type}")
async def get_context(context_type: str, token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    admin_id = payload.get("sub")
    if context_type == "raw":
        ctx = get_raw_context_json(admin_id)
    elif context_type == "structured":
        ctx = get_structured_context_json(admin_id)
    elif context_type == "csv":
        ctx = get_csv_context(admin_id)
    else:
        raise HTTPException(status_code=400, detail="context_type must be 'raw', 'structured', or 'csv'")
    if not ctx:
        raise HTTPException(status_code=404, detail="Context not found")
    return ctx

@router.put("/context/{context_type}")
async def update_context(context_type: str, file: UploadFile = File(...), token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    admin_id = payload.get("sub")
    if context_type == "raw":
        if not file.filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="Only JSON files are allowed.")
        save_raw_context_json(file, admin_id)
    elif context_type == "structured":
        if not file.filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="Only JSON files are allowed.")
        save_structured_context_json(file, admin_id)
    elif context_type == "csv":
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Only CSV files are allowed.")
        save_csv_context(file, admin_id)
    else:
        raise HTTPException(status_code=400, detail="context_type must be 'raw', 'structured', or 'csv'")
    return {"message": f"{context_type.capitalize()} context updated."}

@router.delete("/context/{context_type}")
async def delete_context(context_type: str, token: str = Depends(oauth2_scheme)):
    from service.db import db
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    admin_id = payload.get("sub")
    if context_type == "raw":
        db.raw_contexts.delete_one({"admin_id": admin_id})
    elif context_type == "structured":
        db.structured_contexts.delete_one({"admin_id": admin_id})
    elif context_type == "csv":
        db.csv_contexts.delete_one({"admin_id": admin_id})
    else:
        raise HTTPException(status_code=400, detail="context_type must be 'raw', 'structured', or 'csv'")
    return {"message": f"{context_type.capitalize()} context deleted."}

# RAG+LLM answer endpoint (admin only)
@router.post("/ask")
async def ask_question(
    question: str = Body(..., embed=True),
    token: str = Depends(oauth2_scheme)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        admin_id = payload.get("sub")
        answer = rag_llm_answer(question, admin_id)
        return {"answer": answer}
    except Exception as e:
        return {"answer": f"Error during RAG+LLM: {str(e)}"}

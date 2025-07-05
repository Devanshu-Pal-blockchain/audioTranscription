import os
import json
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
import numpy as np

QDRANT_DB_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'qdrant_db')
MODEL_NAME = 'all-MiniLM-L6-v2'

# Initialize embedding model and Qdrant client
os.makedirs(QDRANT_DB_DIR, exist_ok=True)
qdrant_client = QdrantClient(path=QDRANT_DB_DIR)
embedding_model = SentenceTransformer(MODEL_NAME)

# Helper: chunk JSON into passages
def chunk_json(json_data, context_type=None):
    """
    Chunk context for vector indexing.
    - For raw context: use 'transcribed_segments' (list of dicts with 'text').
    - For structured context: use 'session_summary', 'rocks', 'compliance_log'.
    """
    chunks = []
    # If context_type is not provided, try to infer
    if context_type is None:
        if 'transcribed_segments' in json_data:
            context_type = 'raw'
        elif 'session_summary' in json_data or 'rocks' in json_data:
            context_type = 'structured'
        else:
            context_type = 'unknown'
    if context_type == 'raw':
        for seg in json_data.get('transcribed_segments', []):
            if 'text' in seg:
                chunks.append(seg['text'])
    elif context_type == 'structured':
        if 'session_summary' in json_data:
            chunks.append(json_data['session_summary'])
        for rock in json_data.get('rocks', []):
            base = f"Rock: {rock.get('rock_title')} | Owner: {rock.get('owner')} | Objective: {rock.get('smart_objective')}"
            chunks.append(base)
            for milestone in rock.get('milestones', []):
                week = milestone.get('week', '')
                for task in milestone.get('tasks', []):
                    chunks.append(f"{base} | {week} | Task: {task}")
            if 'review' in rock:
                chunks.append(f"{base} | Review: {rock['review']}")
        if 'compliance_log' in json_data:
            for k, v in json_data['compliance_log'].items():
                chunks.append(f"Compliance Log: {k}: {v}")
    return chunks

def chunk_csv_context(csv_data):
    chunks = []
    if not csv_data:
        return chunks
    for row in csv_data:
        row_str = ", ".join(f"{k}: {v}" for k, v in row.items())
        chunks.append(row_str)
    return chunks

# Index JSON chunks in Qdrant (per admin/context)
def index_json_chunks(json_data, collection_name, context_type=None):
    # Remove old collection if exists
    if collection_name in [c.name for c in qdrant_client.get_collections().collections]:
        qdrant_client.delete_collection(collection_name=collection_name)
    chunks = chunk_json(json_data, context_type=context_type)
    if not chunks:
        return
    embeddings = embedding_model.encode(chunks, show_progress_bar=False)
    qdrant_client.recreate_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=embeddings.shape[1], distance=Distance.COSINE)
    )
    points = [
        PointStruct(id=i, vector=embeddings[i].tolist(), payload={"text": chunks[i]})
        for i in range(len(chunks))
    ]
    qdrant_client.upsert(collection_name=collection_name, points=points)

# Index CSV chunks in Qdrant (per admin/context)
def index_csv_chunks(csv_data, collection_name):
    if collection_name in [c.name for c in qdrant_client.get_collections().collections]:
        qdrant_client.delete_collection(collection_name=collection_name)
    chunks = chunk_csv_context(csv_data)
    if not chunks:
        return
    embeddings = embedding_model.encode(chunks, show_progress_bar=False)
    qdrant_client.recreate_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=embeddings.shape[1], distance=Distance.COSINE)
    )
    points = [
        PointStruct(id=i, vector=embeddings[i].tolist(), payload={"text": chunks[i]})
        for i in range(len(chunks))
    ]
    qdrant_client.upsert(collection_name=collection_name, points=points)

# RAG+LLM answer: always use Qdrant for context retrieval
def rag_llm_answer(question, admin_id, top_k=5):
    # Retrieve top-k relevant chunks from each context type using Qdrant
    context_chunks = {"raw": [], "structured": [], "csv": []}
    import re
    for context_type in ["raw", "structured", "csv"]:
        collection_name = f"{context_type}_{admin_id}"
        if collection_name in [c.name for c in qdrant_client.get_collections().collections]:
            question_emb = embedding_model.encode([question])[0]
            # Advanced filtering for all context types
            search_result = qdrant_client.search(
                collection_name=collection_name,
                query_vector=question_emb.tolist(),
                limit=30 if context_type != "raw" else top_k
            )
            filtered = [hit.payload["text"] for hit in search_result]
            # For structured and CSV, apply deep/detailed filters
            if context_type in ["structured", "csv"]:
                # Try to extract owner, project, week, task, milestone, name, timestamp, dialogue, etc.
                owner_match = re.search(r"for ([a-zA-Z ]+)", question.lower())
                project_match = re.search(r"project ([a-zA-Z ]+)", question.lower())
                week_match = re.search(r"week ?(\w+)", question.lower())
                task_match = re.search(r"task[s]? ([a-zA-Z0-9 ]+)", question.lower())
                milestone_match = re.search(r"milestone[s]? ([a-zA-Z0-9 ]+)", question.lower())
                name_match = re.search(r"name ([a-zA-Z ]+)", question.lower())
                timestamp_match = re.search(r"timestamp ([0-9\-: ]+)", question.lower())
                dialogue_match = re.search(r"dialogue ([a-zA-Z0-9 ,.'!?-]+)", question.lower())
                # Apply combined filters for owner/project and week if both present
                filtered_combined = filtered
                if (owner_match or project_match) and week_match:
                    key_strs = []
                    if owner_match:
                        key_strs.append(owner_match.group(1).strip().lower())
                    if project_match:
                        key_strs.append(project_match.group(1).strip().lower())
                    week_str = week_match.group(1).strip().lower()
                    filtered_combined = [chunk for chunk in filtered if any(k in chunk.lower() for k in key_strs) and (f"week{week_str}" in chunk.lower() or f"week {week_str}" in chunk.lower())]
                    if filtered_combined:
                        filtered = filtered_combined
                else:
                    # Apply individual filters if present
                    if owner_match:
                        owner_name = owner_match.group(1).strip().lower()
                        filtered = [chunk for chunk in filtered if owner_name in chunk.lower()]
                    if project_match:
                        project_name = project_match.group(1).strip().lower()
                        filtered = [chunk for chunk in filtered if project_name in chunk.lower()]
                    if week_match:
                        week_str = week_match.group(1).strip().lower()
                        filtered = [chunk for chunk in filtered if f"week{week_str}" in chunk.lower() or f"week {week_str}" in chunk.lower()]
                if task_match:
                    task_str = task_match.group(1).strip().lower()
                    filtered = [chunk for chunk in filtered if task_str in chunk.lower()]
                if milestone_match:
                    milestone_str = milestone_match.group(1).strip().lower()
                    filtered = [chunk for chunk in filtered if milestone_str in chunk.lower()]
                if name_match:
                    name_str = name_match.group(1).strip().lower()
                    filtered = [chunk for chunk in filtered if name_str in chunk.lower()]
                if timestamp_match:
                    timestamp_str = timestamp_match.group(1).strip().lower()
                    filtered = [chunk for chunk in filtered if timestamp_str in chunk.lower()]
                if dialogue_match:
                    dialogue_str = dialogue_match.group(1).strip().lower()
                    filtered = [chunk for chunk in filtered if dialogue_str in chunk.lower()]
            # If any filtered, use them; else fallback to all retrieved
            context_chunks[context_type] = filtered if filtered else [hit.payload["text"] for hit in search_result]
        
    # Debug: Print retrieved context chunks
    print("[RAG DEBUG] Retrieved context chunks:")
    for ctype, chunks in context_chunks.items():
        print(f"  {ctype}: {len(chunks)} chunks")
        for i, chunk in enumerate(chunks):
            print(f"    [{i+1}] {chunk[:200]}{'...' if len(chunk) > 200 else ''}")
    # If all are empty, return error
    if not any(context_chunks.values()):
        return "No context available in vector DB. Please upload and index your contexts."

    # Prepare professional, structured prompt for LLM with stronger guidance for factual/count questions
    prompt = f"""
You are a highly accurate meeting assistant. You have access to three types of context:
- Raw meeting transcript (unstructured)
- Structured meeting data (JSON: projects, owners, milestones, tasks, etc.)
- Tabular data (CSV: org chart, roles, etc.)

When answering:
- Always prefer structured or tabular data for factual, list, lookup, or count questions (e.g., number of weeks, tasks, projects, owners, etc.).
- If the question asks for a count, list, or lookup, extract and count directly from the structured or tabular context.
- Use the transcript only for conversational context or if the answer is not in the structured/tabular data.
- If you cannot find an answer in any context, say so clearly.
- If the answer requires a number (e.g., how many weeks, tasks, projects), always count from the structured context and state the number explicitly.

Context (raw transcript):
{chr(10).join(context_chunks['raw']) if context_chunks['raw'] else 'N/A'}

Context (structured JSON):
{chr(10).join(context_chunks['structured']) if context_chunks['structured'] else 'N/A'}

Context (CSV):
{chr(10).join(context_chunks['csv']) if context_chunks['csv'] else 'N/A'}

Question: {question}
Answer:
"""
    from langchain_google_genai import GoogleGenerativeAI
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        return "Gemini API key not set."
    # Use a working Gemini model (try gemini-1.5-flash or gemini-pro-1.0)
    # gemini-1.5-flash is widely available and supports text generation
    try:
        llm = GoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=gemini_api_key)
        response = llm.invoke(prompt)
        return response.strip() if isinstance(response, str) else str(response)
    except Exception as e:
        # Fallback to gemini-pro-1.0 if 1.5-flash is not available
        try:
            llm = GoogleGenerativeAI(model="gemini-pro-1.0", google_api_key=gemini_api_key)
            response = llm.invoke(prompt)
            return response.strip() if isinstance(response, str) else str(response)
        except Exception as e2:
            return f"Gemini API error: {str(e2) or str(e)}"

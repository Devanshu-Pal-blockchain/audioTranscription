import json
import os
from typing import Any, Dict
from models.rock import RockPayload

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # For environments without openai installed

def build_llm_prompt(milestones, weeks, duration, milestone_no):
    return f'''
You are an expert EOS (Entrepreneurial Operating System) facilitator and AI assistant.

The user has provided the following data for a strategic rock:
- List of milestones: {milestones}
- Duration: {duration}
- Number of weeks: {weeks}
- Desired number of milestones: {milestone_no}

Instructions:
1. Do NOT change or invent any IDs, names, or unrelated fields. Only work with the milestones, duration, and week/milestone counts provided.
2. If the list of milestones is longer than the number specified (milestone_no), intelligently combine or merge milestones so the final list matches the number specified by the user. Combine related or sequential milestones in a way that preserves the original intent and detail as much as possible.
3. If the list is shorter or equal, just return the milestones as-is (or padded with empty strings if needed).
4. The output should be a list of milestones (length = milestone_no) that best covers the intent and content of the original milestones.
5. Return ONLY the new milestone list as a JSON array, with no extra text or explanation.
'''

def call_llm_with_openai(prompt: str) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o")
    if not OpenAI or not api_key:
        return {"error": "OpenAI not installed or API key not set."}
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are an expert EOS facilitator and business analyst. Only return valid JSON milestone lists."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=2048
    )
    content = response.choices[0].message.content
    try:
        milestones = json.loads(content)
    except Exception:
        # fallback: try to clean up and parse
        try:
            milestones = json.loads(content.strip().strip('`').replace('json', ''))
        except Exception:
            return {"error": "LLM response is not valid JSON.", "raw_response": content}
    return {"milestones": milestones}

def validate_result(result: dict) -> bool:
    # Basic validation: check required fields and types
    required_fields = ["rock_id", "quarter_id", "rock_name", "milestones"]
    for field in required_fields:
        if field not in result:
            return False
    if not isinstance(result["milestones"], list):
        return False
    if not all(isinstance(m, str) for m in result["milestones"]):
        return False
    return True

def process_custom_rock_payload(payload: RockPayload) -> Dict[str, Any]:
    # 1. Prepare LLM input (exclude rock_id, quarter_id, rock_name)
    llm_input = {
        "milestones": payload.milestones,
        "weeks": payload.weeks,
        "duration": payload.duration,
        "milestone_no": payload.milestone_no,
    }
    # 2. Build prompt
    prompt = build_llm_prompt(
        milestones=payload.milestones,
        weeks=payload.weeks,
        duration=payload.duration,
        milestone_no=payload.milestone_no
    )
    # 3. Call LLM (OpenAI)
    llm_response = call_llm_with_openai(prompt)
    if "error" in llm_response:
        return {"error": llm_response["error"], "llm_prompt": prompt, "raw_response": llm_response.get("raw_response")}
    # 4. Combine with original fields
    result = {
        "rock_id": payload.rock_id,
        "quarter_id": payload.quarter_id,
        "rock_name": payload.rock_name,
        "milestones": llm_response["milestones"],
        "weeks": payload.weeks,
        "duration": payload.duration,
        "milestone_no": payload.milestone_no,
        "llm_prompt": prompt  # For transparency/debugging
    }
    # 5. Validate result
    if not validate_result(result):
        return {"error": "Validation failed for the generated milestones data.", "llm_prompt": prompt, "raw_response": llm_response}
    # 6. Save to output file
    file_path = os.path.join(OUTPUT_DIR, "edited_rocks.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    # 7. Return result
    return result 
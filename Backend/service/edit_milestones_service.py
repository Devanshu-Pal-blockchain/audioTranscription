import json
import os
from typing import Any, Dict
from models.rock import RockPayload

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)


import requests

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"

def build_llm_prompt(milestones, original_weeks, new_weeks, milestone_no):
    return f'''
You are an expert EOS (Entrepreneurial Operating System) facilitator and AI assistant specializing in project timeline optimization.

Context:
- Original milestones: {milestones}
- Original duration: {original_weeks} weeks
- New target duration: {new_weeks} weeks  
- Desired number of milestones: {milestone_no}

Task: Optimize and redistribute milestones for compressed timeline

Instructions:
1. MILESTONE CONSOLIDATION: If there are more milestones than the target number ({milestone_no}), intelligently combine related milestones while preserving all critical work items. Merge sequential or complementary tasks that can be executed together.

2. TIMELINE COMPRESSION: Account for the timeline change from {original_weeks} weeks to {new_weeks} weeks. Ensure milestones are feasible within the compressed timeframe.

3. PRIORITY PRESERVATION: Maintain the logical flow and dependencies between milestones. Critical path items should remain distinct.

4. QUALITY ASSURANCE: Each combined milestone should be actionable and measurable within the new timeframe.

5. OUTPUT FORMAT: Return ONLY a JSON array of exactly {milestone_no} milestone strings, with no additional text or formatting.

Example output: ["Combined milestone 1 description", "Combined milestone 2 description", ...]
'''


def call_llm_with_gemini(prompt: str) -> dict:
    if not GEMINI_API_KEY:
        return {"error": "Gemini API key not set."}
    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    data = {
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ]
    }
    try:
        response = requests.post(GEMINI_API_URL, headers=headers, params=params, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        # Gemini returns text in candidates[0]['content']['parts'][0]['text']
        content = result["candidates"][0]["content"]["parts"][0]["text"]
        try:
            milestones = json.loads(content)
        except Exception:
            # fallback: try to clean up and parse
            try:
                milestones = json.loads(content.strip().strip('`').replace('json', ''))
            except Exception:
                return {"error": "LLM response is not valid JSON.", "raw_response": content}
        return {"milestones": milestones}
    except Exception as e:
        return {"error": f"Gemini API error: {e}"}

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

def validate_enhanced_result(result: dict) -> bool:
    """
    Enhanced validation for optimized milestone results
    """
    # Check required top-level fields
    required_fields = ["rock_id", "quarter_id", "rock_name", "optimized_data"]
    for field in required_fields:
        if field not in result:
            return False
    
    # Validate optimized_data structure
    optimized_data = result.get("optimized_data", {})
    if not isinstance(optimized_data.get("milestones"), list):
        return False
    
    if not isinstance(optimized_data.get("weekly_distribution"), list):
        return False
    
    # Validate milestone content
    milestones = optimized_data.get("milestones", [])
    if not all(isinstance(m, str) and m.strip() for m in milestones):
        return False
    
    # Validate weekly distribution structure
    weekly_dist = optimized_data.get("weekly_distribution", [])
    for week_data in weekly_dist:
        if not isinstance(week_data, dict):
            return False
        if "week" not in week_data or "milestones" not in week_data:
            return False
        if not isinstance(week_data["milestones"], list):
            return False
    
    return True

def process_custom_rock_payload(payload: RockPayload) -> Dict[str, Any]:
    """
    Enhanced process to handle milestone optimization and week redistribution
    """
    # 1. Extract original timeline data
    original_milestones = payload.milestones
    original_weeks = len(set([m.get('week', 1) for m in original_milestones])) if isinstance(original_milestones[0], dict) else payload.weeks
    new_weeks = payload.weeks
    target_milestone_count = payload.milestone_no
    
    # 2. Analyze current milestone distribution
    current_analysis = analyze_milestone_distribution(original_milestones, original_weeks)
    compression_metrics = calculate_compression_factor(original_weeks, new_weeks)
    
    # 3. Prepare milestone text for LLM processing
    milestone_texts = []
    if original_milestones:
        for milestone in original_milestones:
            if isinstance(milestone, dict):
                # Extract text from milestone object (title, task, description, etc.)
                text = milestone.get('title') or milestone.get('task') or milestone.get('description') or str(milestone)
                milestone_texts.append(text)
            else:
                milestone_texts.append(str(milestone))
    
    # 4. Build enhanced prompt with timeline compression context
    prompt = build_llm_prompt(
        milestones=milestone_texts,
        original_weeks=original_weeks,
        new_weeks=new_weeks,
        milestone_no=target_milestone_count
    )
    
    # 5. Call LLM (Gemini) for milestone optimization
    llm_response = call_llm_with_gemini(prompt)
    if "error" in llm_response:
        return {
            "error": llm_response["error"], 
            "llm_prompt": prompt, 
            "raw_response": llm_response.get("raw_response"),
            "analysis": current_analysis,
            "compression_metrics": compression_metrics
        }
    
    # 6. Get optimized milestones from LLM
    optimized_milestones = llm_response["milestones"]
    
    # 7. Distribute optimized milestones across new timeline
    weekly_distribution = distribute_milestones_to_weeks(optimized_milestones, new_weeks)
    
    # 8. Prepare comprehensive result
    result = {
        "rock_id": payload.rock_id,
        "quarter_id": payload.quarter_id,
        "rock_name": payload.rock_name,
        "original_data": {
            "milestones": original_milestones,
            "weeks": original_weeks,
            "milestone_count": len(original_milestones)
        },
        "optimized_data": {
            "milestones": optimized_milestones,
            "weeks": new_weeks,
            "milestone_count": len(optimized_milestones),
            "weekly_distribution": weekly_distribution
        },
        "analysis": current_analysis,
        "compression_metrics": compression_metrics,
        "duration": payload.duration,
        "llm_prompt": prompt  # For transparency/debugging
    }
    
    # 9. Validate result
    if not validate_enhanced_result(result):
        return {
            "error": "Validation failed for the optimized milestones data.", 
            "llm_prompt": prompt, 
            "raw_response": llm_response,
            "analysis": current_analysis
        }
    
    # 10. Save to output file with enhanced data
    file_path = os.path.join(OUTPUT_DIR, "optimized_rocks.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # 11. Return result
    return result

def analyze_milestone_distribution(milestones: list, original_weeks: int) -> dict:
    """
    Analyze the current milestone distribution to understand patterns
    """
    if not milestones:
        return {"total_milestones": 0, "avg_per_week": 0, "distribution": []}
    
    total_milestones = len(milestones)
    avg_per_week = total_milestones / original_weeks if original_weeks > 0 else 0
    
    # Simple distribution analysis
    distribution = []
    milestones_per_week = total_milestones // original_weeks
    remainder = total_milestones % original_weeks
    
    for week in range(original_weeks):
        week_milestones = milestones_per_week + (1 if week < remainder else 0)
        distribution.append(week_milestones)
    
    return {
        "total_milestones": total_milestones,
        "avg_per_week": avg_per_week,
        "distribution": distribution,
        "milestones_per_week": milestones_per_week
    }

def distribute_milestones_to_weeks(milestones: list, target_weeks: int) -> list:
    """
    Distribute milestones evenly across the target number of weeks
    Returns a list of weeks with their assigned milestones
    """
    if not milestones or target_weeks <= 0:
        return []
    
    total_milestones = len(milestones)
    base_milestones_per_week = total_milestones // target_weeks
    remainder = total_milestones % target_weeks
    
    weekly_distribution = []
    milestone_index = 0
    
    for week in range(target_weeks):
        # Calculate how many milestones this week should have
        milestones_this_week = base_milestones_per_week + (1 if week < remainder else 0)
        
        # Assign milestones to this week
        week_milestones = []
        for _ in range(milestones_this_week):
            if milestone_index < total_milestones:
                week_milestones.append(milestones[milestone_index])
                milestone_index += 1
        
        weekly_distribution.append({
            "week": week + 1,
            "milestones": week_milestones,
            "milestone_count": len(week_milestones)
        })
    
    return weekly_distribution

def calculate_compression_factor(original_weeks: int, new_weeks: int) -> dict:
    """
    Calculate compression metrics for timeline analysis
    """
    if original_weeks <= 0 or new_weeks <= 0:
        return {"compression_ratio": 1.0, "time_saved": 0, "intensity_increase": 0}
    
    compression_ratio = new_weeks / original_weeks
    time_saved = original_weeks - new_weeks
    intensity_increase = (original_weeks / new_weeks) - 1
    
    return {
        "compression_ratio": round(compression_ratio, 2),
        "time_saved": time_saved,
        "intensity_increase": round(intensity_increase * 100, 1)  # as percentage
    }
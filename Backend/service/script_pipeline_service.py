"""
Pipeline Service - Core pipeline logic for audio processing and ROCKS generation
Extracted from script.py to be reusable by both HTTP routes and CLI
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime
from pydub import AudioSegment
import re
import csv
import demjson3

# Import required libraries
try:
    from groq import Groq
    import google.generativeai as genai
    import spacy
    import demjson3
    import asyncio
    from .db import db
    from .meeting_json_service import save_raw_context_json, save_structured_context_json
    from .data_parser_service import parse_pipeline_response_to_files
except ImportError as e:
    print(f"Missing required library: {e}")
    print("Please install required packages: pip install groq google-generativeai spacy demjson3")
    print("Also install spaCy model: python -m spacy download en_core_web_sm")
    raise

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom logging function for pipeline steps
def log_step_completion(step_name: str):
    """Log step completion with minimal output"""
    print(f"{step_name} completed")

class PipelineService:
    def __init__(self, admin_id: str = "default_admin"):
        # Initialize API clients
        self.groq_client = self._get_groq_client()
        self.gemini_model = self._get_gemini_model()
        
        # Initialize spaCy for NLP processing
        self.nlp = self._get_spacy_model()
        
        # Database settings
        self.admin_id = admin_id
        
    def _get_groq_client(self):
        """Initialize Groq client for transcription"""
        try:
            return Groq()
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {e}")
            raise
    
    def _get_gemini_model(self):
        """Initialize Gemini model for ROCKS generation"""
        try:
            api_key = os.getenv("GEMINI_API_KEY_SCRIPT")
            if not api_key:
                raise ValueError("GEMINI_API_KEY_SCRIPT environment variable not set")
            
            genai.configure(api_key=api_key)
            model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
            return genai.GenerativeModel(model_name)
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}")
            raise
    
    def _get_spacy_model(self):
        """Initialize spaCy model for NLP processing"""
        try:
            return spacy.load("en_core_web_sm")
        except OSError:
            logger.error("Please install spaCy English model: python -m spacy download en_core_web_sm")
            raise
    
    def _save_to_database(self, data: Dict[str, Any], context_type: str) -> bool:
        """Save data directly to MongoDB"""
        try:
            if context_type == "raw":
                # Create a mock file object for the service function
                class MockFile:
                    def __init__(self, content):
                        self.content = json.dumps(content).encode('utf-8')
                    
                    def read(self):
                        return self.content
                    
                    @property
                    def file(self):
                        return self
                
                mock_file = MockFile(data)
                save_raw_context_json(mock_file, self.admin_id)
                
            elif context_type == "structured":
                # Create a mock file object for the service function
                class MockFile:
                    def __init__(self, content):
                        self.content = json.dumps(content).encode('utf-8')
                    
                    def read(self):
                        return self.content
                    
                    @property
                    def file(self):
                        return self
                
                mock_file = MockFile(data)
                save_structured_context_json(mock_file, self.admin_id)
            
            return True
                
        except Exception as e:
            logger.error(f"Error saving to database: {e}")
            return False

    # ==================== SCRIPT 1: AUDIO PROCESSING ====================
    def process_audio(self, audio_path: str) -> Dict[str, Any]:
        """Script 1: Audio processing and transcription"""
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Segment audio into chunks
        chunk_duration_ms = 20 * 60 * 1000  # 20 minutes
        audio = AudioSegment.from_file(audio_path)
        chunks = []
        
        for i in range(0, len(audio), chunk_duration_ms):
            chunk = audio[i:i + chunk_duration_ms]
            chunk_filename = f"temp_chunk_{i//chunk_duration_ms}.webm"
            chunk.export(chunk_filename, format="webm", codec="libopus")
            chunks.append(chunk_filename)
        
        # Transcribe each chunk
        transcription_segments = []
        for i, chunk_path in enumerate(chunks):
            try:
                with open(chunk_path, "rb") as file:
                    transcription = self.groq_client.audio.translations.create(
                        file=(chunk_path, file.read()),
                        model="whisper-large-v3",
                        response_format="verbose_json",
                    )
                
                transcription_segments.append({
                    "index": i,
                    "text": transcription.text
                })
                
            except Exception as e:
                logger.error(f"Error transcribing chunk {i}: {e}")
                transcription_segments.append({"index": i, "text": ""})
            
            # Clean up chunk file
            try:
                os.remove(chunk_path)
            except:
                pass
        
        # Combine all transcriptions
        full_transcript = " ".join([seg["text"] for seg in transcription_segments if seg["text"].strip()])
        
        # Redact company names
        full_transcript = full_transcript.replace("47Billion", "XXXYYYZZZ")
        
        result = {
            "full_transcript": full_transcript,
        }
        
        return result

    # ==================== SCRIPT 2: SEMANTIC TOKENIZATION ====================
    def semantic_tokenization(self, transcription_data: Dict[str, Any]) -> Dict[str, Any]:
        """Script 2: Advanced semantic tokenization using spaCy"""
        full_transcript = transcription_data["full_transcript"]
        
        # Split transcript into segments for processing
        n_segments = 6  # Match original script2.py
        doc = self.nlp(full_transcript)
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        total_sentences = len(sentences)
        seg_size = total_sentences // n_segments
        
        transcriptions = []
        for i in range(n_segments):
            start = i * seg_size
            end = (i + 1) * seg_size if i < n_segments - 1 else total_sentences
            segment = " ".join(sentences[start:end]).strip()
            if segment:
                transcriptions.append(segment)
        
        # Extract semantic tokens from each segment
        semantic_tokens = []
        for i, text in enumerate(transcriptions):
            logger.info(f"Processing segment {i+1}/{len(transcriptions)}")
            doc = self.nlp(text)
            
            segment_tokens = {
                "segment_id": i,
                "text": text,
                "entities": [],
                "key_phrases": [],
                "action_items": [],
                "dates": [],
                "people": [],
                "organizations": [],
                "locations": []
            }
            
            # Extract named entities
            for ent in doc.ents:
                entity_info = {
                    "text": ent.text,
                    "label": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "description": spacy.explain(ent.label_)
                }
                segment_tokens["entities"].append(entity_info)
                
                # Categorize entities
                if ent.label_ in ["PERSON"]:
                    segment_tokens["people"].append(ent.text)
                elif ent.label_ in ["DATE", "TIME"]:
                    segment_tokens["dates"].append(ent.text)
                elif ent.label_ in ["ORG"]:
                    segment_tokens["organizations"].append(ent.text)
                elif ent.label_ in ["GPE", "LOC"]:
                    segment_tokens["locations"].append(ent.text)
            
            # Extract potential action items (sentences with action verbs)
            action_verbs = {
                "complete", "finish", "deliver", "implement", "launch", 
                "create", "build", "develop", "migrate", "close", "finalize",
                "start", "begin", "initiate", "execute", "deploy", "release",
                "review", "analyze", "test", "validate", "approve", "submit"
            }
            
            for sent in doc.sents:
                sent_tokens = [token.lemma_.lower() for token in sent]
                if any(verb in sent_tokens for verb in action_verbs):
                    segment_tokens["action_items"].append(sent.text.strip())
            
            # Extract key noun phrases
            for chunk in doc.noun_chunks:
                if len(chunk.text.split()) > 1:  # Multi-word phrases
                    segment_tokens["key_phrases"].append(chunk.text)
            
            # Remove duplicates
            for key in ["people", "dates", "organizations", "locations", "key_phrases"]:
                segment_tokens[key] = list(set(segment_tokens[key]))
            
            semantic_tokens.append(segment_tokens)
        
        # Generate summary statistics
        total_people = set()
        total_dates = set()
        total_organizations = set()
        total_action_items = []
        total_entities = []
        
        for token in semantic_tokens:
            total_people.update(token["people"])
            total_dates.update(token["dates"])
            total_organizations.update(token["organizations"])
            total_action_items.extend(token["action_items"])
            total_entities.extend(token["entities"])
        
        summary_stats = {
            "total_segments": len(semantic_tokens),
            "unique_people": len(total_people),
            "unique_dates": len(total_dates),
            "unique_organizations": len(total_organizations),
            "total_action_items": len(total_action_items),
            "total_entities": len(total_entities),
            "people_mentioned": list(total_people),
            "dates_mentioned": list(total_dates),
            "organizations_mentioned": list(total_organizations)
        }
        
        logger.info(f"Semantic tokenization completed for {len(transcriptions)} segments")
        
        return {
            "semantic_tokens": semantic_tokens,
            "summary_stats": summary_stats,
            "metadata": {
                "total_segments_processed": len(transcriptions),
                "processing_timestamp": datetime.now().isoformat()
            }
        }

    # ==================== SCRIPT 3: PARALLEL SEGMENT ANALYSIS ====================
    async def parallel_segment_analysis(self, semantic_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Step 3: Process each segment in parallel with LLM"""
        semantic_tokens = semantic_data.get("semantic_tokens", [])
        summary_stats = semantic_data.get("summary_stats", {})
        
        logger.info(f"Starting parallel analysis of {len(semantic_tokens)} segments")
        
        # Process segments in parallel
        tasks = []
        for segment in semantic_tokens:
            task = self._analyze_segment(segment)
            tasks.append(task)
        
        # Wait for all segments to complete
        segment_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        valid_results = []
        for i, result in enumerate(segment_results):
            if isinstance(result, Exception):
                logger.error(f"Error analyzing segment {i}: {result}")
                # Create fallback result
                valid_results.append({
                    "segment_id": i,
                    "analysis": f"Error analyzing segment {i}: {str(result)}",
                    "entities": semantic_tokens[i].get("entities", []),
                    "action_items": semantic_tokens[i].get("action_items", [])
                })
            else:
                valid_results.append(result)
        
        logger.info(f"Parallel segment analysis completed for {len(valid_results)} segments")
        return valid_results

    async def _analyze_segment(self, segment: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single segment with LLM"""
        prompt = f"""
        Analyze this meeting segment and extract key business information.
        
        SEGMENT TEXT:
        {segment["text"]}
        
        EXTRACTED ENTITIES:
        - People: {segment["people"]}
        - Dates: {segment["dates"]}
        - Organizations: {segment["organizations"]}
        - Locations: {segment["locations"]}
        - Action Items: {segment["action_items"]}
        - Key Phrases: {segment["key_phrases"]}
        
        ANALYSIS REQUIREMENTS:
        Please provide a structured analysis focusing on:
        
        1. KEY TOPICS DISCUSSED:
           - Main subjects and themes in this segment
        
        2. ACTION ITEMS IDENTIFIED:
           - Specific tasks, deliverables, or commitments mentioned
        
        3. PEOPLE AND ROLES:
           - Who was mentioned and their involvement
        
        4. TIMELINES AND DEADLINES:
           - Any dates, deadlines, or timeframes mentioned
        
        5. DECISIONS OR AGREEMENTS:
           - Any decisions made or agreements reached
        
        6. PROJECTS OR INITIATIVES:
           - Any projects, initiatives, or strategic items discussed
        
        Focus only on actionable business items. Ignore general discussion, small talk, or technical troubleshooting.
        Structure your response with clear sections and bullet points.
        """
        
        try:
            response = self.gemini_model.generate_content(prompt)
            return {
                "segment_id": segment["segment_id"],
                "analysis": response.text,
                "entities": segment["entities"],
                "action_items": segment["action_items"],
                "people": segment["people"],
                "dates": segment["dates"],
                "organizations": segment["organizations"]
            }
        except Exception as e:
            logger.error(f"Error analyzing segment {segment['segment_id']}: {e}")
            raise

    def _handle_large_response(self, response_text: str, max_tokens_per_chunk: int = 200) -> str:
        """Handle large responses by splitting into manageable chunks"""
        if len(response_text) <= max_tokens_per_chunk:
            return response_text
        
        logger.warning(f"Response too large ({len(response_text)} chars), attempting to extract JSON...")
        
        # Try to find JSON boundaries
        json_start = response_text.find('{')
        json_end = response_text.rfind('}')
        
        if json_start != -1 and json_end != -1 and json_end > json_start:
            extracted_json = response_text[json_start:json_end + 1]
            logger.info(f"Extracted JSON chunk of {len(extracted_json)} characters")
            return extracted_json
        
        # If no clear JSON boundaries, return the first chunk
        logger.warning("No clear JSON boundaries found, returning first chunk")
        return response_text[:max_tokens_per_chunk]

    def participants_to_csv(self, participants: list) -> str:
        """Convert a list of participant dicts to a CSV string with Full Name, Job Role, Responsibilities columns."""
        if not participants:
            return "Full Name,Job Role,Responsibilities"
        lines = ["Full Name,Job Role,Responsibilities"]
        for p in participants:
            name = p.get("employee_name", "")
            role = p.get("employee_designation", "")
            resp = p.get("employee_responsibilities", "")
            lines.append(f'{name},{role},{resp}')
        return "\n".join(lines)

    async def combine_segments_and_generate_rocks(self, segment_analyses: List[Dict[str, Any]], num_weeks: int, participants: list, max_retries: int = 3) -> Dict[str, Any]:
        """Step 4: Combine segment analyses and generate ROCKS in one step"""
        logger.info(f"Combining {len(segment_analyses)} segment analyses and generating ROCKS")
        
        # Prepare segment analyses for LLM
        analyses_text = ""
        total_action_items = []
        all_people = set()
        all_dates = set()
        all_organizations = set()
        
        for analysis in segment_analyses:
            analyses_text += f"""
SEGMENT {analysis['segment_id'] + 1} ANALYSIS:
{analysis['analysis']}

EXTRACTED INFORMATION:
- People: {analysis.get('people', [])}
- Dates: {analysis.get('dates', [])}
- Organizations: {analysis.get('organizations', [])}
- Action Items: {analysis.get('action_items', [])}
---
"""
            total_action_items.extend(analysis.get('action_items', []))
            all_people.update(analysis.get('people', []))
            all_dates.update(analysis.get('dates', []))
            all_organizations.update(analysis.get('organizations', []))
        
        # Generate roles CSV string from participants
        roles_csv = self.participants_to_csv(participants)
        roles_str = roles_csv
        
        # Generate weekly_tasks structure dynamically
        weekly_tasks_structure = self.generate_weekly_tasks_structure(num_weeks)
        
        # Create comprehensive ROCKS generation prompt
        prompt = f"""
        Based on these individual segment analyses, create a structured JSON response following the EOS (Entrepreneurial Operating System) format for quarterly rocks.
        
        MEETING CONTEXT:
        - Total segments analyzed: {len(segment_analyses)}
        - People mentioned: {list(all_people)}
        - Organizations: {list(all_organizations)}
        - Dates mentioned: {list(all_dates)}
        - Action items identified: {len(total_action_items)}
        - Number of weeks: {num_weeks}
        
        AVAILABLE ROLES AND EMPLOYEES (CSV):
        {roles_str}
        
        INSTRUCTIONS:
        - ONLY use the names and designations (job roles) provided in the above CSV for assigning owners to rocks and tasks.
        - DO NOT invent or use any names or positions that are not present in the CSV.
        - If a specific person is not mentioned, choose the most relevant employee from the provided list.
        
        REQUIREMENTS:
        Create a JSON structure with the following format:
        
        {{
            "session_summary": "Brief 2-4 sentence overview of the meeting and key outcomes",
            "rocks": [
                {{
                    "rock_title": "Clear, actionable title for the major initiative",
                    "owner": "Full Name" - extract from analysis or from the above list,
                    "designation":"Job Title" - extract from analysis or from the above list,
                    "smart_objective": "Specific, Measurable, Achievable, Relevant, Time-bound objective with clear success criteria",
                    "weekly_tasks": {weekly_tasks_structure},
                    "review": {{
                        "status": "Approved" or "Pending",
                        "comments": "Any relevant comments or notes"
                    }}
                }}
            ]
        }}
        
        GUIDELINES:
        1. Extract 3-4 major rocks (strategic initiatives) from the segment analyses (MAXIMUM 4 ROCKS)
        2. Each rock should be a significant quarterly objective, not a small task
        3. SMART objectives should include specific metrics and deadlines
        4. Milestones should break down the rock into {num_weeks}
        5. For each week, provide 3-4 distinct tasks in the 'tasks' array (3 to 4 tasks per week)
        6. Each task object must have a 'task_title' field, and may optionally include a 'sub_tasks' array field. Do NOT include a 'task_id' field. Task IDs will be assigned later in the pipeline.
        7. If specific people aren't mentioned, use the most relevant employee and role from the above list. If no suitable match is found, use a generic role as before (e.g., "Project Manager").
        8. If detailed milestones aren't available, create logical weekly progression
        9. Set realistic timelines based on the project scope
        10. KEEP THE RESPONSE CONCISE - focus on the most important initiatives only
        11. AVOID UNNECESSARY CONTENT - give direct, concise descriptions without verbose explanations
        
        IMPORTANT: Your response must be strictly valid JSON. Do not include any incomplete or malformed objects or arrays. Each milestone must be a JSON object with both 'week' and 'tasks' fields, where 'tasks' is an array of 3-4 task objects. Each task object must have a 'task_title' field, and may optionally include a 'sub_tasks' array field. Do NOT include a 'task_id' field. There must be {num_weeks} milestones (one for each week). Do not include any array elements that are not objects. Do not include any extra or duplicate keys. Do not include any trailing commas. The output must be directly parseable by Python's json.loads().
        """
        
        # Retry loop for JSON generation
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Generating ROCKS from segment analyses (attempt {attempt + 1}/{max_retries + 1})...")
                
                response = self.gemini_model.generate_content(prompt)
                json_response = self._handle_large_response(response.text.strip())
                
                # Clean up response
                json_response = re.sub(r"^```(?:json)?\s*", "", json_response)
                json_response = re.sub(r"\s*```$", "", json_response)
                json_response = re.sub(r',([ \t\r\n]*[\]}])', r'\1', json_response)
                
                logger.info("Raw JSON response received")
                
                # Parse and validate JSON - try standard json first, then demjson3 as fallback
                rocks_data = None
                json_error = None
                demjson_error = None
                
                try:
                    rocks_data = json.loads(json_response)
                    logger.info("JSON parsed successfully with standard json module")
                except json.JSONDecodeError as e:
                    json_error = e
                    logger.warning(f"Standard JSON parsing failed, trying demjson3: {e}")
                    try:
                        rocks_data = demjson3.decode(json_response)
                        logger.info("JSON parsed successfully with demjson3")
                    except Exception as de:
                        demjson_error = de
                        logger.error(f"Both JSON parsing methods failed. Standard error: {e}, Demjson3 error: {de}")
                        logger.error(f"Raw response: {json_response}")
                        
                        # If this is not the last attempt, continue to retry
                        if attempt < max_retries:
                            logger.warning(f"Invalid JSON generated on attempt {attempt + 1}. Retrying...")
                            continue
                        else:
                            return {
                                "error": "Invalid JSON format generated after all retry attempts",
                                "raw_response": json_response,
                                "standard_json_error": str(json_error),
                                "demjson3_error": str(demjson_error),
                                "attempts_made": max_retries + 1
                            }
                
                # If we get here, JSON parsing was successful
                # Add compliance log
                rocks_data["compliance_log"] = {
                    "transcription_tool": "Python Speech Recognition",
                    "genai_model": f"Gemini {self.gemini_model.model_name}",
                    "facilitator_review_timestamp": datetime.now().isoformat(),
                    "data_storage_platform": "Local Processing",
                    "processing_pipeline_version": "1.0",
                    "generation_attempts": attempt + 1
                }
                
                logger.info(f"ROCKS generated successfully from segment analyses on attempt {attempt + 1}")
                return rocks_data
                
            except Exception as e:
                logger.error(f"Error generating ROCKS from segment analyses on attempt {attempt + 1}: {e}")
                if attempt < max_retries:
                    logger.warning(f"Retrying ROCKS generation...")
                    continue
                else:
                    return {"error": str(e), "attempts_made": max_retries + 1}

    # ==================== SCRIPT 4: ROCKS GENERATION ====================
    def generate_weekly_tasks_structure(self, num_weeks: int) -> str:
        """Generate the weekly_tasks structure dynamically (without task_id)"""
        structure_parts = []
        for week_num in range(1, num_weeks + 1):
            week_structure = f'''                        {{"week": {week_num}, "tasks": [
                            {{"task_title": "Task 1 description", "sub_tasks": []}},
                            {{"task_title": "Task 2 description", "sub_tasks": ["Subtask 2.1", "Subtask 2.2"]}},
                            {{"task_title": "Task 3 description", "sub_tasks": []}},
                            {{"task_title": "Task 4 description", "sub_tasks": []}}
                        ]}}'''
            structure_parts.append(week_structure)
        return f"[\n{',\n'.join(structure_parts)}\n                    ]"

    async def generate_rocks(self, analysis_result: Dict[str, Any], num_weeks: int, max_retries: int = 3) -> Dict[str, Any]:
        """Script 4: ROCKS generation using Gemini with retry mechanism"""
        
        analysis_text = analysis_result.get('analysis', '')
        input_summary = analysis_result.get('input_summary', {})
        
        # Generate weekly_tasks structure dynamically
        weekly_tasks_structure = self.generate_weekly_tasks_structure(num_weeks)
        
        prompt = f"""
        Based on the following comprehensive meeting analysis, create a structured JSON response following the EOS (Entrepreneurial Operating System) format for quarterly rocks.
        
        MEETING ANALYSIS:
        {analysis_text}
        
        CONTEXT:
        - Total segments processed: {input_summary.get('total_segments', 0)}
        - Action items identified: {input_summary.get('action_items_count', 0)}
        - People involved: {input_summary.get('people_mentioned', 0)}
        - Number of weeks: {num_weeks}
        
        REQUIREMENTS:
        Create a JSON structure with the following format:
        
        {{
            "session_summary": "Brief 2-4 sentence overview of the meeting and key outcomes",
            "rocks": [
                {{
                    "rock_title": "Clear, actionable title for the major initiative",
                    "owner": "Full Name (Job Title)" - extract from analysis or from the above list,
                    "smart_objective": "Specific, Measurable, Achievable, Relevant, Time-bound objective with clear success criteria",
                    "weekly_tasks": {weekly_tasks_structure},
                    "review": {{
                        "status": "Approved" or "Pending",
                        "comments": "Any relevant comments or notes"
                    }}
                }}
            ]
        }}
        
        GUIDELINES:
        1. Extract 3-4 major rocks (strategic initiatives) from the analysis
        2. Each rock should be a significant quarterly objective, not a small task
        3. SMART objectives should include specific metrics and deadlines
        4. Milestones should break down the rock into {num_weeks} weekly actionable tasks (one milestone per week)
        5. For each week, provide 3-4 distinct tasks in the 'tasks' array (3 to 4 tasks per week)
        6. Each task object must have a 'task_title' field, and may optionally include a 'sub_tasks' array field. Do NOT include a 'task_id' field. Task IDs will be assigned later in the pipeline.
        7. If specific people aren't mentioned, use the most relevant employee and role from the above list. If no suitable match is found, use a generic role as before (e.g., "Project Manager").
        8. If detailed milestones aren't available, create logical weekly progression
        9. Set realistic timelines based on the project scope
        10. KEEP THE RESPONSE CONCISE - focus on the most important initiatives only
        11. AVOID UNNECESSARY CONTENT - give direct, concise descriptions without verbose explanations
        
        IMPORTANT: Your response must be strictly valid JSON. Do not include any incomplete or malformed objects or arrays. Each milestone must be a JSON object with both 'week' and 'tasks' fields, where 'tasks' is an array of 3-4 task objects. Each task object must have a 'task_title' field, and may optionally include a 'sub_tasks' array field. Do NOT include a 'task_id' field. There must be {num_weeks} milestones (one for each week). Do not include any array elements that are not objects. Do not include any extra or duplicate keys. Do not include any trailing commas. The output must be directly parseable by Python's json.loads().
        """
        
        # Retry loop for JSON generation
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Generating ROCKS JSON structure (attempt {attempt + 1}/{max_retries + 1})...")
                
                response = self.gemini_model.generate_content(prompt)
                json_response = self._handle_large_response(response.text.strip())
                
                # Clean up response
                json_response = re.sub(r"^```(?:json)?\s*", "", json_response)
                json_response = re.sub(r"\s*```$", "", json_response)
                json_response = re.sub(r',([ \t\r\n]*[\]}])', r'\1', json_response)
                
                logger.info("Raw JSON response received")
                
                # Parse and validate JSON - try standard json first, then demjson3 as fallback
                rocks_data = None
                json_error = None
                demjson_error = None
                
                try:
                    rocks_data = json.loads(json_response)
                    logger.info("JSON parsed successfully with standard json module")
                except json.JSONDecodeError as e:
                    json_error = e
                    logger.warning(f"Standard JSON parsing failed, trying demjson3: {e}")
                    try:
                        rocks_data = demjson3.decode(json_response)
                        logger.info("JSON parsed successfully with demjson3")
                    except Exception as de:
                        demjson_error = de
                        logger.error(f"Both JSON parsing methods failed. Standard error: {e}, Demjson3 error: {de}")
                        logger.error(f"Raw response: {json_response}")
                        
                        # If this is not the last attempt, continue to retry
                        if attempt < max_retries:
                            logger.warning(f"Invalid JSON generated on attempt {attempt + 1}. Retrying...")
                            continue
                        else:
                            return {
                                "error": "Invalid JSON format generated after all retry attempts",
                                "raw_response": json_response,
                                "standard_json_error": str(json_error),
                                "demjson3_error": str(demjson_error),
                                "attempts_made": max_retries + 1
                            }
                
                # If we get here, JSON parsing was successful
                # Add compliance log
                rocks_data["compliance_log"] = {
                    "transcription_tool": "Python Speech Recognition",
                    "genai_model": f"Gemini {self.gemini_model.model_name}",
                    "facilitator_review_timestamp": datetime.now().isoformat(),
                    "data_storage_platform": "Local Processing",
                    "processing_pipeline_version": "1.0",
                    "generation_attempts": attempt + 1
                }
                
                logger.info(f"ROCKS JSON generated and validated successfully on attempt {attempt + 1}")
                return rocks_data
                
            except Exception as e:
                logger.error(f"Error generating ROCKS on attempt {attempt + 1}: {e}")
                if attempt < max_retries:
                    logger.warning(f"Retrying ROCKS generation...")
                    continue
                else:
                    return {"error": str(e), "attempts_made": max_retries + 1}
    
    def validate_rocks_structure(self, rocks_data: Dict[str, Any], num_weeks: int) -> Dict[str, Any]:
        """Validate the generated ROCKS structure"""
        validation_result = {
            "valid": True,
            "issues": [],
            "suggestions": []
        }
        
        # Check required fields
        if "session_summary" not in rocks_data:
            validation_result["issues"].append("Missing session_summary")
            validation_result["valid"] = False
        
        if "rocks" not in rocks_data:
            validation_result["issues"].append("Missing rocks array")
            validation_result["valid"] = False
        else:
            rocks = rocks_data["rocks"]
            if not isinstance(rocks, list):
                validation_result["issues"].append("rocks should be an array")
                validation_result["valid"] = False
            
            # Validate each rock
            for i, rock in enumerate(rocks):
                required_fields = ["rock_title", "owner", "smart_objective", "weekly_tasks", "review"]
                for field in required_fields:
                    if field not in rock:
                        validation_result["issues"].append(f"Rock {i+1} missing {field}")
                        validation_result["valid"] = False
                
                # Check number of weeks
                if "weekly_tasks" in rock and isinstance(rock["weekly_tasks"], list):
                    if len(rock["weekly_tasks"]) != num_weeks:
                        validation_result["issues"].append(f"Rock {i+1} has {len(rock['weekly_tasks'])} weeks, expected {num_weeks}")
                        validation_result["valid"] = False
                
                # Check weekly_tasks structure
                if "weekly_tasks" in rock and isinstance(rock["weekly_tasks"], list):
                    for j, week in enumerate(rock["weekly_tasks"]):
                        if not isinstance(week, dict) or "week" not in week or "tasks" not in week:
                            validation_result["issues"].append(f"Rock {i+1}, week {j+1} has invalid structure")
                            validation_result["valid"] = False
                        else:
                            # Check tasks structure
                            tasks = week["tasks"]
                            if not isinstance(tasks, list):
                                validation_result["issues"].append(f"Rock {i+1}, week {j+1} tasks is not an array")
                                validation_result["valid"] = False
                            else:
                                for k, task in enumerate(tasks):
                                    if not isinstance(task, dict) or "task_title" not in task:
                                        validation_result["issues"].append(f"Rock {i+1}, week {j+1}, task {k+1} has invalid structure")
                                        validation_result["valid"] = False
        
        # Generate suggestions
        if validation_result["valid"]:
            validation_result["suggestions"].append("Structure looks good! Consider reviewing deadlines and resource allocation.")
        
        return validation_result

    # ==================== MAIN PIPELINE FUNCTION ====================
    async def run_pipeline(self, audio_file: str, num_weeks: int, quarter_id: str, participants: list) -> Dict[str, Any]:
        """Run the complete pipeline"""
        try:
            # Create timestamp for file naming
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_prefix = f"pipeline_{timestamp}"
            
            # Step 1: Audio Processing
            transcription_data = self.process_audio(audio_file)
            log_step_completion("Step 1: Audio Processing")
            
            # Step 2: Semantic Tokenization
            semantic_data = self.semantic_tokenization(transcription_data)
            log_step_completion("Step 2: Semantic Tokenization")
            
            # Step 3: Parallel Segment Analysis
            segment_analyses = await self.parallel_segment_analysis(semantic_data)
            log_step_completion("Step 3: Parallel Segment Analysis")
            
            # Step 4: Combine Segments and Generate ROCKS
            rocks_data = await self.combine_segments_and_generate_rocks(segment_analyses, num_weeks, participants)
            
            # Check if ROCKS generation failed
            if "error" in rocks_data:
                logger.error(f"ROCKS generation failed: {rocks_data['error']}")
                return rocks_data
            
            # Validate ROCKS structure
            validation = self.validate_rocks_structure(rocks_data, num_weeks)
            if not validation["valid"]:
                logger.warning("ROCKS structure validation issues found:")
                for issue in validation["issues"]:
                    logger.warning(f"  - {issue}")
            
            log_step_completion("Step 4: ROCKS Generation")
            
            # Create final response (only ROCKS data)
            final_response = rocks_data
            
            # Save final response
            final_file = "final_response.json"
            with open(final_file, "w", encoding="utf-8") as f:
                json.dump(final_response, f, indent=2, ensure_ascii=False)
            
            # Parse final response into Rock and Task collections, always passing quarter_id and participants
            log_step_completion("Step 5: Data Parsing")
            rocks_file, tasks_file = parse_pipeline_response_to_files(final_response, file_prefix, quarter_id, participants)
            
            if rocks_file and tasks_file:
                logger.info(f"Parsed data saved to: {rocks_file} and {tasks_file}")
            else:
                logger.error("Failed to parse and save data")
            
            print("Pipeline completed successfully!")
            
            return final_response
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            return {"error": str(e), "status": "failed"}

# Convenience function for easy usage
async def run_pipeline_for_audio(audio_file: str, num_weeks: int, quarter_id: str, participants: list, admin_id: str = "default_admin") -> Dict[str, Any]:
    """Convenience function to run pipeline for a given audio file"""
    pipeline = PipelineService(admin_id)
    return await pipeline.run_pipeline(audio_file, num_weeks, quarter_id, participants) 
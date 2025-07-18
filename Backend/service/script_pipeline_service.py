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
from dotenv import load_dotenv

# Load environment variables from the Backend directory
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(backend_dir, '.env')
load_dotenv(env_path)

# Import required libraries
try:
    from groq import Groq
    from openai import OpenAI
    import spacy
    import demjson3
    import asyncio
    from .db import db
    from .meeting_json_service import save_raw_context_json, save_structured_context_json
    from .data_parser_service import parse_pipeline_response_to_files
except ImportError as e:
    print(f"Missing required library: {e}")
    print("Please install required packages: pip install groq openai spacy demjson3")
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
    def __init__(self, facilitator_id: str = "default_facilitator"):
        # Initialize API clients
        self.groq_client = self._get_groq_client()
        self.openai_client = self._get_openai_client()
        
        # Initialize spaCy for NLP processing
        self.nlp = self._get_spacy_model()
        
        # Database settings
        self.facilitator_id = facilitator_id
        
    def _get_groq_client(self):
        """Initialize Groq client for transcription"""
        try:
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY environment variable not set")
            return Groq(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {e}")
            raise
    
    def _get_openai_client(self):
        """Initialize OpenAI client for ROCKS generation"""
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            logger.info(f"Using OpenAI API key: {api_key}...")  # Log first 4 chars for debugging-
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            
            # Initialize with extended timeout for large responses
            return OpenAI(
                api_key=api_key,
                timeout=120.0  # 2 minutes timeout for large responses
            )
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
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
                save_raw_context_json(mock_file, self.facilitator_id)
                
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
                save_structured_context_json(mock_file, self.facilitator_id)
            
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
        """Script 2: Enhanced semantic tokenization using spaCy for comprehensive analysis"""
        
        # DYNAMIC SEGMENTATION CONFIGURATION
        # Adjust these parameters to fine-tune segmentation behavior
        SEGMENTATION_CONFIG = {
            "target_words_per_segment": 150,  # Optimal for LLM processing
            "target_chars_per_segment": 1000,  # Backup measure for dense content
            "min_segments": 4,  # Minimum segments for any transcript
            "max_segments": 50,  # Maximum to prevent excessive API calls
            "quality_threshold": 50,  # Minimum words per segment for quality
        }
        
        # Robust extraction of transcript text with fallback options
        full_transcript = ""
        
        if isinstance(transcription_data, dict):
            # Try multiple possible keys
            if "full_transcript" in transcription_data:
                full_transcript = transcription_data["full_transcript"]
            elif "transcript" in transcription_data:
                full_transcript = transcription_data["transcript"]
            elif "content" in transcription_data:
                full_transcript = transcription_data["content"]
            elif "text" in transcription_data:
                full_transcript = transcription_data["text"]
            else:
                # If no recognized key, try to convert the entire dict to string
                full_transcript = json.dumps(transcription_data)
                logger.warning("No recognized transcript key found, using entire dict as string")
        else:
            # If it's not a dict, convert to string
            full_transcript = str(transcription_data)
            logger.warning("Transcription data is not a dict, converting to string")
        
        # Ensure we have some content
        if not full_transcript or full_transcript.strip() == "":
            raise ValueError("No transcript content found to process")
        
        # DEBUG: Print word count and transcript info
        word_count = len(full_transcript.split())
        print(f"=== TRANSCRIPT DEBUG INFO ===")
        print(f"Total character count: {len(full_transcript)}")
        print(f"Total word count: {word_count}")
        print(f"First 200 characters: {full_transcript[:200]}...")
        print(f"Last 200 characters: ...{full_transcript[-200:]}")
        print(f"=== END TRANSCRIPT DEBUG ===")
        
        logger.info(f"Processing transcript with {len(full_transcript)} characters and {word_count} words")
        
        # Enhanced segmentation for longer meetings - create more granular segments
        # for better detail extraction while maintaining manageable chunk sizes
        # DYNAMIC SEGMENTATION based on transcript size for better accuracy
        
        # Calculate optimal number of segments based on transcript characteristics
        target_words_per_segment = SEGMENTATION_CONFIG["target_words_per_segment"]
        target_chars_per_segment = SEGMENTATION_CONFIG["target_chars_per_segment"]
        min_segments = SEGMENTATION_CONFIG["min_segments"]
        max_segments = SEGMENTATION_CONFIG["max_segments"]
        
        # Calculate segments based on word count
        segments_by_words = max(min_segments, min(max_segments, word_count // target_words_per_segment))
        
        # Also consider character count for very dense content
        segments_by_chars = max(min_segments, min(max_segments, len(full_transcript) // target_chars_per_segment))
        
        # Use the higher value to ensure detailed analysis
        n_segments = max(segments_by_words, segments_by_chars)
        
        # Ensure we have at least minimum segments
        n_segments = max(min_segments, n_segments)
        
        # DEBUG: Show dynamic segmentation calculation
        print(f"=== DYNAMIC SEGMENTATION CALCULATION ===")
        print(f"Total words: {word_count}")
        print(f"Total characters: {len(full_transcript)}")
        print(f"Target words per segment: {target_words_per_segment}")
        print(f"Target chars per segment: {target_chars_per_segment}")
        print(f"Min segments: {min_segments}, Max segments: {max_segments}")
        print(f"Segments by words: {segments_by_words}")
        print(f"Segments by chars: {segments_by_chars}")
        print(f"Final n_segments (dynamic): {n_segments}")
        print(f"Expected words per segment: {word_count // n_segments if n_segments > 0 else 0}")
        print(f"Expected chars per segment: {len(full_transcript) // n_segments if n_segments > 0 else 0}")
        print(f"=== END DYNAMIC SEGMENTATION ===")
        doc = self.nlp(full_transcript)
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        total_sentences = len(sentences)
        seg_size = total_sentences // n_segments
        
        # DEBUG: Print segmentation info
        print(f"=== SEGMENTATION DEBUG INFO ===")
        print(f"Total sentences found: {total_sentences}")
        print(f"Number of segments to create (DYNAMIC): {n_segments}")
        print(f"Sentences per segment: {seg_size}")
        print(f"Remaining sentences for last segment: {total_sentences - (seg_size * (n_segments - 1))}")
        print(f"Segmentation is now DYNAMIC based on transcript size!")
        print(f"=== END SEGMENTATION DEBUG ===")
        
        # Create initial segments
        initial_segments = []
        for i in range(n_segments):
            start = i * seg_size
            end = (i + 1) * seg_size if i < n_segments - 1 else total_sentences
            segment = " ".join(sentences[start:end]).strip()
            if segment:
                initial_segments.append(segment)
        
        # Filter out empty segments and apply quality control
        quality_threshold = SEGMENTATION_CONFIG["quality_threshold"]
        transcriptions = []
        low_quality_segments = []
        
        for i, seg in enumerate(initial_segments):
            if seg.strip():
                segment_word_count = len(seg.split())
                if segment_word_count >= quality_threshold:
                    transcriptions.append(seg)
                    # DEBUG: Print segment info
                    print(f"Segment {len(transcriptions)}: {segment_word_count} words, {len(seg)} characters")
                else:
                    low_quality_segments.append((i+1, segment_word_count))
        
        # If we have low quality segments, try to merge them with adjacent segments
        if low_quality_segments:
            print(f"WARNING: {len(low_quality_segments)} segments below quality threshold ({quality_threshold} words)")
            for seg_num, word_count in low_quality_segments:
                print(f"  Segment {seg_num}: {word_count} words")
        
        # If we have too few segments after filtering, adjust
        if len(transcriptions) < min_segments:
            print(f"WARNING: Only {len(transcriptions)} segments created, less than minimum {min_segments}")
            print("This might happen with very short transcripts")
        
        # DEBUG: Print final segment statistics
        print(f"=== FINAL SEGMENT STATS ===")
        print(f"Total segments created: {len(transcriptions)}")
        total_segment_words = sum(len(seg.split()) for seg in transcriptions)
        print(f"Total words in all segments: {total_segment_words}")
        print(f"Word count difference: {word_count - total_segment_words}")
        print(f"Average words per segment: {total_segment_words // len(transcriptions) if transcriptions else 0}")
        print(f"Average characters per segment: {sum(len(seg) for seg in transcriptions) // len(transcriptions) if transcriptions else 0}")
        print(f"Segments above quality threshold: {len(transcriptions)}")
        print(f"Low quality segments filtered out: {len(low_quality_segments)}")
        print(f"=== END SEGMENT STATS ===")
        
        # Extract enhanced semantic tokens from each segment
        semantic_tokens = []
        for i, text in enumerate(transcriptions):
            logger.info(f"Processing segment {i+1}/{len(transcriptions)} with enhanced analysis")
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
                "locations": [],
                "monetary_values": [],
                "percentages": [],
                "technologies": [],
                "products": [],
                "processes": [],
                "metrics": [],
                "projects": [],
                "departments": [],
                "priorities": [],
                "risks": [],
                "opportunities": [],
                "deadlines": [],
                "dependencies": []
            }
            
            # Enhanced named entity extraction
            for ent in doc.ents:
                entity_info = {
                    "text": ent.text,
                    "label": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "description": ent.label_,
                    "confidence": getattr(ent, 'confidence', 1.0)
                }
                segment_tokens["entities"].append(entity_info)
                
                # Enhanced entity categorization
                if ent.label_ in ["PERSON"]:
                    segment_tokens["people"].append(ent.text)
                elif ent.label_ in ["DATE", "TIME"]:
                    segment_tokens["dates"].append(ent.text)
                elif ent.label_ in ["ORG"]:
                    segment_tokens["organizations"].append(ent.text)
                elif ent.label_ in ["GPE", "LOC"]:
                    segment_tokens["locations"].append(ent.text)
                elif ent.label_ in ["MONEY"]:
                    segment_tokens["monetary_values"].append(ent.text)
                elif ent.label_ in ["PERCENT"]:
                    segment_tokens["percentages"].append(ent.text)
                elif ent.label_ in ["PRODUCT"]:
                    segment_tokens["products"].append(ent.text)
            
            # Enhanced action item extraction with more comprehensive verb patterns
            action_verbs = {
                # Completion/Delivery verbs
                "complete", "finish", "deliver", "implement", "launch", "finalize", "conclude",
                # Creation/Development verbs  
                "create", "build", "develop", "design", "architect", "construct", "generate",
                # Process/Operational verbs
                "migrate", "deploy", "release", "execute", "process", "handle", "manage",
                # Initiation verbs
                "start", "begin", "initiate", "commence", "establish", "setup", "configure",
                # Analysis/Review verbs
                "review", "analyze", "evaluate", "assess", "audit", "investigate", "research",
                # Validation/Quality verbs
                "test", "validate", "verify", "approve", "certify", "quality-check",
                # Communication/Coordination verbs
                "coordinate", "communicate", "present", "report", "update", "inform", "notify",
                # Planning/Strategy verbs
                "plan", "schedule", "organize", "strategize", "prioritize", "allocate",
                # Improvement/Optimization verbs
                "improve", "optimize", "enhance", "streamline", "automate", "scale",
                # Problem-solving verbs
                "resolve", "fix", "troubleshoot", "debug", "solve", "address", "handle"
            }
            
            # Enhanced pattern matching for action items
            for sent in doc.sents:
                sent_text = sent.text.strip()
                sent_tokens = [token.lemma_.lower() for token in sent]
                
                # Check for action verbs
                if any(verb in sent_tokens for verb in action_verbs):
                    segment_tokens["action_items"].append(sent_text)
                
                # Check for deadline patterns
                deadline_patterns = ["by", "due", "deadline", "before", "until", "no later than"]
                if any(pattern in sent_text.lower() for pattern in deadline_patterns):
                    segment_tokens["deadlines"].append(sent_text)
                
                # Check for dependency patterns
                dependency_patterns = ["depends on", "requires", "needs", "after", "once", "following"]
                if any(pattern in sent_text.lower() for pattern in dependency_patterns):
                    segment_tokens["dependencies"].append(sent_text)
                
                # Check for priority indicators
                priority_patterns = ["priority", "urgent", "critical", "important", "high priority", "asap"]
                if any(pattern in sent_text.lower() for pattern in priority_patterns):
                    segment_tokens["priorities"].append(sent_text)
                
                # Check for risk indicators
                risk_patterns = ["risk", "concern", "issue", "problem", "challenge", "blocker", "obstacle"]
                if any(pattern in sent_text.lower() for pattern in risk_patterns):
                    segment_tokens["risks"].append(sent_text)
                
                # Check for opportunity indicators
                opportunity_patterns = ["opportunity", "potential", "could", "might", "possibility", "chance"]
                if any(pattern in sent_text.lower() for pattern in opportunity_patterns):
                    segment_tokens["opportunities"].append(sent_text)
            
            # Extract enhanced key noun phrases and technical terms
            for chunk in doc.noun_chunks:
                if len(chunk.text.split()) > 1:  # Multi-word phrases
                    phrase = chunk.text.strip()
                    segment_tokens["key_phrases"].append(phrase)
                    
                    # Categorize specific types of phrases
                    phrase_lower = phrase.lower()
                    
                    # Technology-related terms
                    tech_keywords = ["system", "platform", "software", "application", "database", "api", "tool", 
                                   "framework", "infrastructure", "cloud", "server", "integration", "automation"]
                    if any(keyword in phrase_lower for keyword in tech_keywords):
                        segment_tokens["technologies"].append(phrase)
                    
                    # Process-related terms
                    process_keywords = ["process", "workflow", "procedure", "methodology", "approach", "strategy",
                                      "framework", "model", "pipeline", "lifecycle", "governance"]
                    if any(keyword in phrase_lower for keyword in process_keywords):
                        segment_tokens["processes"].append(phrase)
                    
                    # Project-related terms
                    project_keywords = ["project", "initiative", "program", "effort", "campaign", "rollout",
                                      "implementation", "migration", "transformation", "upgrade"]
                    if any(keyword in phrase_lower for keyword in project_keywords):
                        segment_tokens["projects"].append(phrase)
                    
                    # Department/team-related terms
                    dept_keywords = ["team", "department", "group", "division", "unit", "squad", "committee",
                                   "engineering", "marketing", "sales", "hr", "finance", "operations", "legal"]
                    if any(keyword in phrase_lower for keyword in dept_keywords):
                        segment_tokens["departments"].append(phrase)
                    
                    # Metrics/KPI-related terms
                    metrics_keywords = ["metric", "kpi", "measurement", "target", "goal", "objective", "rate",
                                      "percentage", "score", "index", "benchmark", "performance", "analytics"]
                    if any(keyword in phrase_lower for keyword in metrics_keywords):
                        segment_tokens["metrics"].append(phrase)
            
            # Remove duplicates from all lists (except entities which contain dicts)
            for key in segment_tokens:
                if isinstance(segment_tokens[key], list):
                    if key == "entities":
                        # For entities (which are dicts), use a different approach to remove duplicates
                        seen = set()
                        unique_entities = []
                        for entity in segment_tokens[key]:
                            # Create a unique identifier for each entity based on text and label
                            entity_id = (entity.get("text", ""), entity.get("label", ""))
                            if entity_id not in seen:
                                seen.add(entity_id)
                                unique_entities.append(entity)
                        segment_tokens[key] = unique_entities
                    else:
                        # For other lists containing strings, use set to remove duplicates
                        segment_tokens[key] = list(set(segment_tokens[key]))
            
            semantic_tokens.append(segment_tokens)
        
        # Generate enhanced summary statistics
        all_categories = {
            "people": set(), "dates": set(), "organizations": set(), "locations": set(),
            "monetary_values": set(), "percentages": set(), "technologies": set(),
            "products": set(), "processes": set(), "metrics": set(), "projects": set(),
            "departments": set(), "priorities": [], "risks": [], "opportunities": [],
            "deadlines": [], "dependencies": [], "action_items": [], "entities": []
        }
        
        for token in semantic_tokens:
            for category, values in all_categories.items():
                if category in token:
                    if isinstance(values, set):
                        # For sets, only add hashable items (strings)
                        if category == "entities":
                            # Skip entities here, handle separately
                            continue
                        else:
                            # Add string items to sets
                            values.update(token[category])
                    else:
                        # For lists, extend normally
                        values.extend(token[category])
            
            # Handle entities separately (they are dictionaries, not hashable)
            all_categories["entities"].extend(token.get("entities", []))
        
        # Convert sets to lists for JSON serialization
        for category, values in all_categories.items():
            if isinstance(values, set):
                all_categories[category] = list(values)
        
        summary_stats = {
            "total_segments": len(semantic_tokens),
            "enhanced_extraction": True,
            "segment_size": f"Average {len(transcriptions[0].split()) if transcriptions else 0} words per segment",
            **{f"unique_{k}": len(v) if isinstance(v, list) else 0 for k, v in all_categories.items()},
            **{f"{k}_mentioned": v for k, v in all_categories.items()}
        }
        
        logger.info(f"Enhanced semantic tokenization completed for {len(transcriptions)} segments with comprehensive extraction")
        
        return {
            "semantic_tokens": semantic_tokens,
            "summary_stats": summary_stats,
            "metadata": {
                "total_segments_processed": len(transcriptions),
                "processing_timestamp": datetime.now().isoformat(),
                "enhancement_level": "comprehensive",
                "extraction_categories": list(all_categories.keys())
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
        """Analyze a single segment with LLM using Chain of Thought reasoning"""
        
        # Enhanced CoT prompt for better extraction and assignment accuracy
        prompt = f"""
        You are an expert business meeting analyst. Use step-by-step reasoning to analyze this meeting segment thoroughly.

        MEETING SEGMENT:
        {segment["text"]}
        
        EXTRACTED ENTITIES FOR REFERENCE:
        - People: {segment["people"]}
        - Dates: {segment["dates"]}
        - Organizations: {segment["organizations"]}
        - Action Items: {segment["action_items"]}
        - Key Phrases: {segment["key_phrases"]}
        
        ## CHAIN OF THOUGHT ANALYSIS PROCESS:
        
        ### STEP 1: SPEAKER AND CONTEXT IDENTIFICATION
        Let me first identify who is speaking and in what context:
        - Who are the main speakers in this segment?
        - What are their roles and responsibilities?
        - What is the main topic/theme being discussed?
        - What is the business context and strategic importance?
        
        ### STEP 2: TASK AND RESPONSIBILITY EXTRACTION
        Now let me systematically extract tasks and responsibilities:
        - Is anyone explicitly assigning tasks to others?
        - Is anyone volunteering or committing to do something?
        - Are there implicit responsibilities based on roles and discussion?
        - What are the specific deliverables and outcomes expected?
        
        ### STEP 3: ASSIGNMENT VALIDATION AND MAPPING
        For each task/responsibility identified, let me validate:
        - Who specifically is being assigned this task?
        - Is this person clearly mentioned by name?
        - What is their role and why are they suitable for this task?
        - Is the assignment explicit or implicit?
        - Are there any deadline or timeline constraints?
        
        ### STEP 4: CATEGORIZATION AND PRIORITIZATION
        Let me categorize each item based on scope and timeline:
        - Is this a runtime solution (solved immediately in the meeting)?
        - Is this a short-term todo (< 14 days)?
        - Is this a strategic rock (quarterly initiative)?
        - What is the business impact and priority level?
        
        ### STEP 5: COMPREHENSIVE SYNTHESIS
        Finally, let me synthesize all findings with complete context:
        - What are the key business themes and strategic implications?
        - How do the assignments relate to overall business goals?
        - What are the dependencies and interconnections?
        - What follow-up actions or communications are needed?
        
        ## DETAILED ANALYSIS OUTPUT:
        Based on my step-by-step analysis above, provide a comprehensive structured response covering:
        
        1. **SPEAKER AND CONTEXT ANALYSIS:**
           - Primary speakers and their roles
           - Main discussion topics and themes
           - Strategic business context and importance
           - Decision-making authority and influence patterns
        
        2. **TASK AND RESPONSIBILITY EXTRACTION:**
           For EACH task/responsibility identified:
           - Exact task description with full context
           - Person assigned (use exact names, be specific)
           - Assigning authority (who gave the assignment)
           - Timeline and deadline information
           - Success criteria and deliverables
           - Dependencies and prerequisites
           - Resource requirements
           - Classification: runtime_solution, todo, or potential_rock
        
        3. **PEOPLE AND ROLE VALIDATION:**
           For EACH person mentioned:
           - Full name and role/title
           - Specific contributions to the discussion
           - Tasks they were assigned or volunteered for
           - Their authority level and decision-making capacity
           - Relationships with other participants
        
        4. **BUSINESS CONTEXT AND STRATEGIC IMPLICATIONS:**
           - How this segment relates to broader business objectives
           - Strategic importance and urgency
           - Cross-functional impact and dependencies
           - Customer or stakeholder implications
           - Risk factors and mitigation needs
        
        5. **TIMELINE AND DEPENDENCIES:**
           - All dates, deadlines, and timeframes mentioned
           - Sequence of activities and critical path items
           - Dependencies between tasks and people
           - Potential bottlenecks or scheduling conflicts
        
        6. **DECISIONS AND COMMITMENTS:**
           - Specific decisions made and by whom
           - Commitments and agreements reached
           - Alternatives considered and rationale
           - Implementation approach and next steps
        
        CRITICAL REQUIREMENTS:
        - Be extremely specific about names and assignments
        - Don't make assumptions about who should do what
        - Only assign tasks to people explicitly mentioned
        - Provide complete context for every extracted item
        - Use exact quotes when possible for task descriptions
        - Identify any ambiguities or unclear assignments
        - Focus on actionable items with clear ownership
        
        Think through each step methodically and provide your detailed analysis.
        """
        
        try:
            model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            response = self.openai_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are an expert business analyst who uses systematic step-by-step reasoning to extract detailed insights from meeting segments. Think through each step methodically to ensure no tasks or assignments are missed, and be extremely precise about task ownership and context."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent, focused analysis
                max_tokens=4000   # Adjusted for gpt-4o-mini - reduced from 8000 to 4000
            )
            
            analysis_content = response.choices[0].message.content or ""
            logger.info(f"Segment {segment['segment_id']} analysis length: {len(analysis_content)} characters")
            
            return {
                "segment_id": segment["segment_id"],
                "analysis": analysis_content,
                "entities": segment["entities"],
                "action_items": segment["action_items"],
                "people": segment["people"],
                "dates": segment["dates"],
                "organizations": segment["organizations"]
            }
        except Exception as e:
            logger.error(f"Error analyzing segment {segment['segment_id']}: {e}")
            raise

    def _handle_large_response(self, response_text: str, max_tokens_per_chunk: int = 100000) -> str:
        """Handle large responses by splitting into manageable chunks"""
        # Increased limit from 200 to 100,000 characters to accommodate large responses
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
        
        # If no clear JSON boundaries, return a larger chunk
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

    def aggregate_segment_insights(self, segment_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate insights from all segments to provide comprehensive context for ROCKS generation"""
        
        # Aggregate all extracted information
        aggregated_insights = {
            "comprehensive_themes": [],
            "strategic_initiatives": [],
            "operational_improvements": [],
            "cross_functional_projects": [],
            "technology_initiatives": [],
            "process_enhancements": [],
            "risk_management_items": [],
            "opportunity_areas": [],
            "stakeholder_commitments": {},
            "timeline_analysis": {},
            "resource_requirements": {},
            "dependency_mapping": [],
            "priority_classification": {}
        }
        
        # Collect all themes and categorize them
        all_themes = []
        all_projects = []
        all_risks = []
        all_opportunities = []
        all_deadlines = []
        all_dependencies = []
        
        for analysis in segment_analyses:
            analysis_text = analysis.get('analysis', '')
            
            # Extract strategic themes
            if 'strategic' in analysis_text.lower() or 'initiative' in analysis_text.lower():
                aggregated_insights["strategic_initiatives"].append({
                    "segment_id": analysis.get('segment_id'),
                    "content": analysis_text[:500],  # First 500 chars for context
                    "entities": analysis.get('entities', []),
                    "people": analysis.get('people', [])
                })
            
            # Extract operational improvements
            if any(keyword in analysis_text.lower() for keyword in ['improve', 'optimize', 'enhance', 'streamline', 'efficiency']):
                aggregated_insights["operational_improvements"].append({
                    "segment_id": analysis.get('segment_id'),
                    "content": analysis_text[:500],
                    "action_items": analysis.get('action_items', [])
                })
            
            # Extract technology-related discussions
            if any(keyword in analysis_text.lower() for keyword in ['system', 'platform', 'software', 'technology', 'tool', 'automation']):
                aggregated_insights["technology_initiatives"].append({
                    "segment_id": analysis.get('segment_id'),
                    "content": analysis_text[:500],
                    "technologies": getattr(analysis, 'technologies', [])
                })
            
            # Extract cross-functional items
            if any(keyword in analysis_text.lower() for keyword in ['team', 'department', 'cross-functional', 'coordinate', 'collaborate']):
                aggregated_insights["cross_functional_projects"].append({
                    "segment_id": analysis.get('segment_id'),
                    "content": analysis_text[:500],
                    "people": analysis.get('people', [])
                })
            
            # Aggregate stakeholder commitments
            for person in analysis.get('people', []):
                if person not in aggregated_insights["stakeholder_commitments"]:
                    aggregated_insights["stakeholder_commitments"][person] = []
                aggregated_insights["stakeholder_commitments"][person].append({
                    "segment": analysis.get('segment_id'),
                    "context": analysis_text[:200],
                    "action_items": analysis.get('action_items', [])
                })
        
        # Generate comprehensive context summary
        aggregated_insights["context_summary"] = {
            "total_strategic_initiatives": len(aggregated_insights["strategic_initiatives"]),
            "total_operational_improvements": len(aggregated_insights["operational_improvements"]),
            "total_technology_initiatives": len(aggregated_insights["technology_initiatives"]),
            "total_cross_functional_projects": len(aggregated_insights["cross_functional_projects"]),
            "unique_stakeholders": len(aggregated_insights["stakeholder_commitments"]),
            "complexity_indicators": {
                "high_coordination_required": len(aggregated_insights["cross_functional_projects"]) > 2,
                "significant_technology_component": len(aggregated_insights["technology_initiatives"]) > 1,
                "multiple_strategic_tracks": len(aggregated_insights["strategic_initiatives"]) > 3
            }
        }
        
        return aggregated_insights

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

    async def generate_rocks(self, segment_analyses: List[Dict[str, Any]], num_weeks: int, participants: list, max_retries: int = 3) -> Dict[str, Any]:
        """Generate ROCKS from a list of segment analyses (combines segments and generates rocks in one step)"""
        logger.info(f"Combining {len(segment_analyses)} segment analyses and generating comprehensive ROCKS")
        
        # First, aggregate insights for better context
        aggregated_insights = self.aggregate_segment_insights(segment_analyses)
        
        # Prepare segment analyses for LLM with enhanced context
        analyses_text = ""
        total_action_items = []
        all_people = set()
        all_dates = set()
        all_organizations = set()
        
        for analysis in segment_analyses:
            analyses_text += f"""
SEGMENT {analysis['segment_id'] + 1} COMPREHENSIVE ANALYSIS:
{analysis['analysis']}

EXTRACTED INFORMATION:
- People: {analysis.get('people', [])}
- Dates: {analysis.get('dates', [])}
- Organizations: {analysis.get('organizations', [])}
- Action Items: {analysis.get('action_items', [])}
- Technologies: {analysis.get('technologies', [])}
- Projects: {analysis.get('projects', [])}
- Departments: {analysis.get('departments', [])}
- Priorities: {analysis.get('priorities', [])}
- Risks: {analysis.get('risks', [])}
- Opportunities: {analysis.get('opportunities', [])}
- Metrics: {analysis.get('metrics', [])}
- Deadlines: {analysis.get('deadlines', [])}
- Dependencies: {analysis.get('dependencies', [])}
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
        # Create comprehensive ROCKS generation prompt with Chain of Thought reasoning
        prompt = f"""
        You are a Master EOS Facilitator and Strategic Business Analyst. Use systematic Chain of Thought reasoning to extract maximum value from this comprehensive meeting analysis.

        ## PARTICIPANT VALIDATION (CRITICAL):
        **OFFICIAL PARTICIPANTS LIST:**
        {roles_str}
        
        **MANDATORY ASSIGNMENT RULES:**
        - ONLY assign tasks, todos, issues, and rocks to participants listed above
        - Use EXACT full names from the participants list
        - If assignment is unclear or person not in list, use "UNASSIGNED"
        - Do NOT make assumptions about who should be assigned
        
        ## CHAIN OF THOUGHT ANALYSIS PROCESS:

        ### STEP 1: COMPREHENSIVE CONTEXT ANALYSIS
        Let me first understand the full context of this {len(segment_analyses)}-segment meeting:
        - What are the main strategic themes and business objectives discussed?
        - Who are the key decision makers and their areas of responsibility?
        - What are the urgent issues and long-term strategic initiatives?
        - How do the different segments connect to form a coherent business strategy?
        
        ### STEP 2: PARTICIPANT MAPPING AND ROLE VALIDATION
        Now let me map each participant to their responsibilities and areas of expertise:
        - What specific roles do they have in the organization?
        - What areas of the business are they responsible for?
        - What tasks and projects were they explicitly assigned or volunteered for?
        - What is their capacity and authority level for different types of work?
        
        ### STEP 3: ISSUE IDENTIFICATION AND CATEGORIZATION  
        Let me systematically identify and categorize all issues discussed:
        - What problems or challenges were explicitly raised?
        - What is the business impact and urgency of each issue?
        - Who raised each issue and who has ownership to resolve it?
        - How should each issue be categorized (runtime solution, todo, or strategic rock)?
        
        ### STEP 4: TASK AND RESPONSIBILITY EXTRACTION
        Now let me extract all tasks and responsibilities with clear ownership:
        - What specific tasks were assigned to specific people?
        - What commitments and volunteer actions were made?
        - What are the timelines and deliverables for each task?
        - How do these tasks support the broader strategic objectives?
        
        ### STEP 5: STRATEGIC ROCKS FORMULATION
        Let me formulate comprehensive strategic rocks (quarterly goals):
        - What are the major strategic initiatives that emerged from the discussion?
        - How can I group related tasks and objectives into coherent quarterly goals?
        - Who is the best owner for each strategic initiative based on their role?
        - What are the specific, measurable outcomes for each rock?
        
        ### STEP 6: MILESTONE AND TIMELINE DEVELOPMENT
        Finally, let me develop detailed weekly milestones for each rock:
        - How should each {num_weeks}-week timeline be structured?
        - What are the logical progression and dependencies between milestones?
        - What resources and checkpoints are needed each week?
        - How do the milestones build toward the quarterly objective?

        ## COMPREHENSIVE MEETING ANALYTICS:
        - **Total Segments Analyzed**: {len(segment_analyses)} (indicating extensive strategic meeting)
        - **Unique Participants**: {list(all_people)}
        - **Organizations Involved**: {list(all_organizations)}
        - **Timeline References**: {list(all_dates)}
        - **Total Action Items Identified**: {len(total_action_items)}
        - **Strategic Planning Period**: {num_weeks} weeks
        
        **AGGREGATED STRATEGIC INSIGHTS**:
        - Strategic Initiatives: {aggregated_insights['context_summary']['total_strategic_initiatives']}
        - Operational Improvements: {aggregated_insights['context_summary']['total_operational_improvements']}
        - Technology Initiatives: {aggregated_insights['context_summary']['total_technology_initiatives']}
        - Cross-Functional Projects: {aggregated_insights['context_summary']['total_cross_functional_projects']}
        - Complexity Indicators: {aggregated_insights['context_summary']['complexity_indicators']}

        **DETAILED SEGMENT ANALYSES**:
        {analyses_text}

        ## BASED ON MY CHAIN OF THOUGHT ANALYSIS ABOVE, GENERATE COMPREHENSIVE OUTPUT:

        Your response must be valid JSON with this exact structure:

        {{
            "session_summary": {{
                "meeting_overview": "Comprehensive overview of all major themes, strategic decisions, and organizational impact based on my Step 1 analysis",
                "strategic_themes": "Detailed analysis of strategic direction and business transformation initiatives from Step 1",
                "participant_roles": "Summary of key participants and their areas of responsibility from Step 2",
                "issues_landscape": "Overview of all challenges and improvement opportunities from Step 3",
                "task_allocation": "Summary of task assignments and responsibility distribution from Step 4",
                "strategic_direction": "Analysis of quarterly rocks and strategic initiatives from Step 5",
                "implementation_timeline": "Overview of milestone progression and timeline from Step 6"
            }},
            "issues": [
                // Generate 8-15 issues based on Step 3 analysis
                {{
                    "issue_title": "Specific, descriptive title from Step 3 analysis",
                    "description": "Comprehensive description including business impact and context",
                    "raised_by": "EXACT Full Name from participants list ONLY - use 'UNASSIGNED' if not in list",
                    "discussion_notes": "Key discussion points and proposed approaches",
                    "urgency_level": "High | Medium | Low",
                    "linked_solution_type": "rock | todo | runtime_solution",
                    "linked_solution_ref": "Exact title of related solution"
                }}
            ],
            "runtime_solutions": [
                // Generate 5-10 immediate solutions based on Step 3-4 analysis
                {{
                    "solution_title": "Immediate solution implemented during meeting",
                    "description": "Detailed implementation and outcomes",
                    "assigned_to": "EXACT Full Name from participants list ONLY - use 'UNASSIGNED' if not in list",
                    "designation": "Exact job title from participants list",
                    "deadline": "YYYY-MM-DD format",
                    "success_criteria": "Measurable outcomes"
                }}
            ],
            "todos": [
                // Generate 10-20 short-term tasks based on Step 4 analysis
                {{
                    "task_title": "Specific actionable task from Step 4 analysis",
                    "description": "Comprehensive scope and requirements",
                    "assigned_to": "EXACT Full Name from participants list ONLY - use 'UNASSIGNED' if not in list",
                    "designation": "Exact job title from participants list",
                    "due_date": "YYYY-MM-DD (within 14 days)",
                    "priority_level": "High | Medium | Low",
                    "linked_issue": "Title of related issue from issues array"
                }}
            ],
            "rocks": [
                // Generate 15-25 comprehensive strategic rocks based on Step 5-6 analysis
                {{
                    "rock_owner": "EXACT Full Name from participants list ONLY - use 'UNASSIGNED' if not in list",
                    "designation": "Exact job title from participants list",
                    "smart_rock": "Specific, Measurable, Achievable, Relevant, Time-bound quarterly objective",
                    "business_justification": "Why this rock is strategically important based on Step 1 context",
                    "success_metrics": [
                        "Specific KPI 1 with target value",
                        "Specific KPI 2 with target value"
                    ],
                    "milestones": [
                        // CRITICAL: Generate milestones for ALL {num_weeks} weeks based on Step 6 analysis
                        {{
                            "week": 1,
                            "milestones": [
                                "Specific milestone 1 with clear deliverable",
                                "Specific milestone 2 with measurable outcome"
                            ]
                        }},
                        {{
                            "week": 2,
                            "milestones": [
                                "Week 2 milestone with detailed scope"
                            ]
                        }}
                        // CONTINUE FOR ALL {num_weeks} WEEKS - DO NOT STOP AT WEEK 2
                        // Generate week 3, 4, 5... up to week {num_weeks}
                    ],
                    "linked_issues": ["Related issue titles from issues array"]
                }}
            ]
        }}

        ## CRITICAL REQUIREMENTS:
        1. **SYSTEMATIC THINKING**: Apply the 6-step Chain of Thought process above
        2. **PARTICIPANT VALIDATION**: Only assign to people in the official participants list
        3. **COMPREHENSIVE EXTRACTION**: Extract every actionable item and strategic initiative
        4. **COMPLETE MILESTONES**: Generate milestones for ALL {num_weeks} weeks, not just 1-2
        5. **SPECIFIC ASSIGNMENTS**: Be extremely precise about who is assigned what
        6. **VALID JSON**: Return only valid JSON with no additional text

        Think through each step systematically and generate the most comprehensive response possible.
        """
        
        # Retry loop for JSON generation
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Generating ROCKS from segment analyses (attempt {attempt + 1}/{max_retries + 1})...")
                model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # Changed from gpt-4o to gpt-4o-mini
                response = self.openai_client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are a master EOS facilitator and business analyst creating comprehensive ROCKS (quarterly goals) from extensive meeting analyses. Generate maximum detail and extract every strategic initiative. Return only valid JSON with comprehensive detail."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    max_tokens=16000  # Adjusted to 16000 for gpt-4o-mini (max limit is ~16,384)
                )
                response_content = response.choices[0].message.content or ""
                logger.info(f"Raw response length: {len(response_content)} characters")
                
                # Only call _handle_large_response if the response is actually problematic
                if len(response_content) > 90000:  # Only truncate if extremely large
                    logger.warning(f"Response is extremely large ({len(response_content)} chars), extracting JSON...")
                    json_response = self._handle_large_response(response_content.strip())
                else:
                    logger.info(f"Response size is acceptable ({len(response_content)} chars), using full response")
                    json_response = response_content.strip()
                
                # Clean up response
                json_response = re.sub(r"^```(?:json)?\s*", "", json_response)
                json_response = re.sub(r"\s*```$", "", json_response)
                json_response = re.sub(r',([ \t\r\n]*[\]}])', r'\1', json_response)
                logger.info("Raw JSON response received")
                
                # DEBUG: Print JSON structure info
                logger.info(f"JSON response length after cleanup: {len(json_response)} characters")
                logger.info(f"JSON response first 500 chars: {json_response[:500]}...")
                if len(json_response) > 1000:
                    logger.info(f"JSON response last 500 chars: ...{json_response[-500:]}")
                
                # Parse and validate JSON - try standard json first, then demjson3 as fallback
                rocks_data = None
                json_error = None
                demjson_error = None
                try:
                    rocks_data = json.loads(json_response)
                    logger.info("JSON parsed successfully with standard json module")
                    
                    # DEBUG: Log the structure we got
                    logger.info(f"Parsed JSON keys: {list(rocks_data.keys()) if isinstance(rocks_data, dict) else 'Not a dict'}")
                    if isinstance(rocks_data, dict):
                        if "rocks" in rocks_data:
                            logger.info(f"Number of rocks found: {len(rocks_data['rocks'])}")
                        if "todos" in rocks_data:
                            logger.info(f"Number of todos found: {len(rocks_data['todos'])}")
                        if "issues" in rocks_data:
                            logger.info(f"Number of issues found: {len(rocks_data['issues'])}")
                        if "runtime_solutions" in rocks_data:
                            logger.info(f"Number of runtime solutions found: {len(rocks_data['runtime_solutions'])}")
                    
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
                model_name = os.getenv("OPENAI_MODEL", "gpt-4o")
                rocks_data["compliance_log"] = {
                    "transcription_tool": "Python Speech Recognition",
                    "genai_model": f"OpenAI {model_name}",
                    "facilitator_review_timestamp": datetime.now().isoformat(),
                    "data_storage_platform": "Local Processing",
                    "processing_pipeline_version": "1.0",
                    "generation_attempts": attempt + 1
                }
                # After parsing the model's JSON response, replace the placeholder with the actual attempt count
                if "compliance_log" in rocks_data and isinstance(rocks_data["compliance_log"], dict):
                    if rocks_data["compliance_log"].get("generation_attempts") == "<GEN_ATTEMPTS>":
                        rocks_data["compliance_log"]["generation_attempts"] = attempt + 1
                logger.info(f"ROCKS generated successfully from segment analyses on attempt {attempt + 1}")
                return rocks_data
            except Exception as e:
                logger.error(f"Error generating ROCKS from segment analyses on attempt {attempt + 1}: {e}")
                if attempt < max_retries:
                    logger.warning(f"Retrying ROCKS generation...")
                    continue
                else:
                    return {"error": str(e), "attempts_made": max_retries + 1}

    def validate_rocks_structure(self, rocks_data: Dict[str, Any], num_weeks: int) -> Dict[str, Any]:
        """Validate the generated ROCKS structure (new format)"""
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
            for i, rock in enumerate(rocks):
                required_fields = ["rock_owner", "designation", "smart_rock", "milestones", "linked_issues"]
                for field in required_fields:
                    if field not in rock:
                        validation_result["issues"].append(f"Rock {i+1} missing {field}")
                        validation_result["valid"] = False
                # Check milestones structure
                if "milestones" in rock and isinstance(rock["milestones"], list):
                    for j, milestone in enumerate(rock["milestones"]):
                        if not isinstance(milestone, dict) or "week" not in milestone:
                            validation_result["issues"].append(f"Rock {i+1}, milestone {j+1} missing 'week' or is not a dict")
                            validation_result["valid"] = False
                        # Must have either 'milestones' (list) or 'milestone' (string)
                        if "milestones" in milestone:
                            if not isinstance(milestone["milestones"], list):
                                validation_result["issues"].append(f"Rock {i+1}, milestone {j+1} 'milestones' is not a list")
                                validation_result["valid"] = False
                        elif "milestone" in milestone:
                            if not isinstance(milestone["milestone"], str):
                                validation_result["issues"].append(f"Rock {i+1}, milestone {j+1} 'milestone' is not a string")
                                validation_result["valid"] = False
                        else:
                            validation_result["issues"].append(f"Rock {i+1}, milestone {j+1} missing 'milestones' or 'milestone'")
                            validation_result["valid"] = False
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

            # Save transcript to raw context collection in DB
            self._save_to_database(transcription_data, context_type="raw")

            # Step 2: Semantic Tokenization
            semantic_data = self.semantic_tokenization(transcription_data)
            log_step_completion("Step 2: Semantic Tokenization")
            
            # Step 3: Parallel Segment Analysis
            segment_analyses = await self.parallel_segment_analysis(semantic_data)
            log_step_completion("Step 3: Parallel Segment Analysis")
            
            # Step 4: Generate ROCKS
            rocks_data = await self.generate_rocks(segment_analyses, num_weeks, participants)
            
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
            import os
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)
            final_file = os.path.join(output_dir, "final_response.json")
            with open(final_file, "w", encoding="utf-8") as f:
                json.dump(final_response, f, indent=2, ensure_ascii=False)
            
            # Parse final response into Rock and Task collections, always passing quarter_id and participants
            log_step_completion("Step 5: Data Parsing")
            rocks_file, tasks_file, todos_file, issues_file, runtime_solutions_file = await parse_pipeline_response_to_files(final_response, file_prefix, quarter_id, participants)
            
            if rocks_file and tasks_file:
                logger.info(f"Parsed data saved to: {rocks_file} and {tasks_file}")
            else:
                logger.error("Failed to parse and save data")
            
            print("Pipeline completed successfully!")
            
            return final_response
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            return {"error": str(e), "status": "failed"}

    async def run_pipeline_for_transcript(self, transcript_json: dict, num_weeks: int, quarter_id: str, participants: list) -> dict:
        """
        Run the pipeline starting from step 2 (semantic tokenization), using a provided transcript JSON.
        """
        try:
            from service.data_parser_service import parse_pipeline_response_to_files
            from datetime import datetime
            # Create timestamp for file naming
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_prefix = f"pipeline_{timestamp}"

            # Extract transcript text from various possible structures
            transcript_text = ""
            if isinstance(transcript_json, dict):
                # Extract transcript text from various possible structures
                if "full_transcript" in transcript_json:
                    transcript_text = transcript_json["full_transcript"]
                elif "transcript" in transcript_json:
                    transcript_text = transcript_json["transcript"]
                elif "content" in transcript_json:
                    transcript_text = transcript_json["content"]
                elif "text" in transcript_json:
                    transcript_text = transcript_json["text"]
                else:
                    # If none of the expected keys exist, convert the entire JSON to string
                    transcript_text = json.dumps(transcript_json)
            else:
                # If it's not a dict, convert to string
                transcript_text = str(transcript_json)
            
            # Validate content quality before processing
            transcript_text = transcript_text.strip()
            word_count = len(transcript_text.split())
            
            # DEBUG: Print detailed transcript info before processing
            print(f"=== PIPELINE TRANSCRIPT DEBUG ===")
            print(f"Original transcript_json type: {type(transcript_json)}")
            print(f"Original transcript_json keys: {list(transcript_json.keys()) if isinstance(transcript_json, dict) else 'Not a dict'}")
            print(f"Extracted transcript_text length: {len(transcript_text)} characters")
            print(f"Extracted transcript_text word count: {word_count}")
            print(f"First 300 chars of transcript_text: {transcript_text[:300]}...")
            print(f"Last 300 chars of transcript_text: ...{transcript_text[-300:]}")
            print(f"=== END PIPELINE TRANSCRIPT DEBUG ===")
            
            logger.info(f"Transcript content validation: {word_count} words, length: {len(transcript_text)} chars")
            
            # Content validation with informative response
            if word_count < 20:  # Less than 20 words is likely insufficient for business analysis
                warning_msg = f"Transcript contains only {word_count} words and may not generate meaningful business insights. "
                warning_msg += "For best results, provide meeting content with discussions about goals, tasks, responsibilities, or action items."
                
                logger.warning(f"Insufficient content for analysis: {warning_msg}")
                logger.info(f"Content preview: '{transcript_text[:200]}...'")
                
                # Return empty results with informative message instead of failing
                empty_result = {
                    "rocks": [],
                    "todos": [],
                    "issues": [],
                    "runtime_solutions": [],
                    "session_summary": {
                        "total_segments": 0,
                        "total_rocks": 0,
                        "total_todos": 0,
                        "total_issues": 0,
                        "total_runtime_solutions": 0,
                        "analysis_note": warning_msg,
                        "content_preview": transcript_text[:200],
                        "word_count": word_count
                    }
                }
                
                # Still save the files so user can see the analysis
                result = await parse_pipeline_response_to_files(empty_result, quarter_id, self.facilitator_id)
                return result

            # Step 2: Semantic Tokenization (convert transcript_json to expected format)
            # The semantic_tokenization method expects a dict with 'full_transcript' key
            transcript_data = {"full_transcript": transcript_text}
            semantic_data = self.semantic_tokenization(transcript_data)
            log_step_completion("Step 2: Semantic Tokenization (from transcript)")

            # Step 3: Parallel Segment Analysis
            segment_analyses = await self.parallel_segment_analysis(semantic_data)
            log_step_completion("Step 3: Parallel Segment Analysis")

            # Step 4: Generate ROCKS
            rocks_data = await self.generate_rocks(segment_analyses, num_weeks, participants)

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
            rocks_file, tasks_file, todos_file, issues_file, runtime_solutions_file = await parse_pipeline_response_to_files(final_response, file_prefix, quarter_id, participants)

            if rocks_file and tasks_file:
                logger.info(f"Parsed data saved to: {rocks_file} and {tasks_file}")
            else:
                logger.error("Failed to parse and save data")

            print("Pipeline (from transcript) completed successfully!")

            return final_response

        except Exception as e:
            logger.error(f"Pipeline from transcript failed: {e}")
            return {"error": str(e), "status": "failed"}

    # ==================== AUDIO TRANSCRIPTION METHOD ====================
    async def transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe a single audio file to text
        Used for processing individual chunks during recording
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dict containing transcription text and metadata
        """
        logger.info(f"Starting transcription for: {audio_path}")
        
        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found: {audio_path}")
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Check file size
        file_size = os.path.getsize(audio_path)
        logger.info(f"Audio file size: {file_size} bytes")
        
        if file_size == 0:
            logger.error(f"Audio file is empty: {audio_path}")
            raise Exception(f"Audio file is empty: {audio_path}")
        
        try:
            # Try to get audio duration (this will test if the file is valid)
            try:
                audio = AudioSegment.from_file(audio_path)
                duration_seconds = len(audio) / 1000.0
                logger.info(f"Audio duration: {duration_seconds} seconds")
            except Exception as audio_error:
                logger.warning(f"Could not process audio with pydub (this is normal for WebM files): {audio_error}")
                # For WebM chunks from browser, we might not be able to get duration without ffmpeg
                # This is okay - we'll just set duration to 0 and let Groq handle the file
                duration_seconds = 0
            
            # Transcribe using Groq - read file content first
            logger.info(f"Reading file for transcription: {audio_path}")
            with open(audio_path, "rb") as file:
                file_content = file.read()
                logger.info(f"File content size: {len(file_content)} bytes")
                
                if len(file_content) == 0:
                    raise Exception("Audio file content is empty")
                
                # Reset file pointer and transcribe
                file.seek(0)
                transcription = self.groq_client.audio.translations.create(
                    file=(os.path.basename(audio_path), file_content),
                    model="whisper-large-v3",
                    response_format="verbose_json",
                )
            
            # Redact company names
            transcript_text = transcription.text.replace("47Billion", "XXXYYYZZZ")
            
            result = {
                "text": transcript_text,
                "duration": duration_seconds,
                "language": getattr(transcription, 'language', 'en'),
                "confidence": getattr(transcription, 'confidence', None)
            }
            
            logger.info(f"Transcription successful: {len(transcript_text)} characters")
            log_step_completion("Audio transcription")
            return result
            
        except Exception as e:
            logger.error(f"Error transcribing audio {audio_path}: {e}")
            # Log more details about the error
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error details: {str(e)}")
            raise Exception(f"Failed to transcribe audio: {str(e)}")


# Convenience functions for standalone usage
async def run_pipeline_for_audio(audio_file: str, num_weeks: int, quarter_id: str, participants: list, facilitator_id: str = "default_facilitator") -> Dict[str, Any]:
    """Convenience function to run pipeline for a given audio file"""
    pipeline = PipelineService(facilitator_id)
    return await pipeline.run_pipeline(audio_file, num_weeks, quarter_id, participants)

async def run_pipeline_for_transcript(transcript_json: dict, num_weeks: int, quarter_id: str, participants: list, facilitator_id: str = "default_facilitator") -> dict:
    """
    Convenience function to run pipeline for a given transcript JSON
    """
    pipeline = PipelineService(facilitator_id)
    return await pipeline.run_pipeline_for_transcript(transcript_json, num_weeks, quarter_id, participants)

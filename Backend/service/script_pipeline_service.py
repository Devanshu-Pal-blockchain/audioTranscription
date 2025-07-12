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
    def __init__(self, admin_id: str = "default_admin"):
        # Initialize API clients
        self.groq_client = self._get_groq_client()
        self.openai_client = self._get_openai_client()
        
        # Initialize spaCy for NLP processing
        self.nlp = self._get_spacy_model()
        
        # Database settings
        self.admin_id = admin_id
        
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
            
            return OpenAI(api_key=api_key)
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
        """Script 2: Enhanced semantic tokenization using spaCy for comprehensive analysis"""
        full_transcript = transcription_data["full_transcript"]
        
        # Enhanced segmentation for longer meetings - create more granular segments
        # for better detail extraction while maintaining manageable chunk sizes
        n_segments = 12  # Increased from 6 to capture more detail from long meetings
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
        """Analyze a single segment with LLM"""
        prompt = f"""
        You are an expert business meeting analyst specializing in comprehensive extraction and deep analysis of meeting content. This segment is part of a potentially long meeting (2-10 hours), so thoroughness and detail are critical.

        SEGMENT TEXT:
        {segment["text"]}
        
        EXTRACTED ENTITIES:
        - People: {segment["people"]}
        - Dates: {segment["dates"]}
        - Organizations: {segment["organizations"]}
        - Locations: {segment["locations"]}
        - Action Items: {segment["action_items"]}
        - Key Phrases: {segment["key_phrases"]}
        
        COMPREHENSIVE ANALYSIS REQUIREMENTS:
        Provide a detailed, structured analysis covering ALL relevant aspects:
        
        1. **DETAILED KEY TOPICS & THEMES:**
           - Primary business subjects discussed in depth
           - Secondary topics and sub-themes
           - Context and background information mentioned
           - Strategic implications and business impact
           - Any technical or operational details discussed
        
        2. **COMPREHENSIVE ACTION ITEMS ANALYSIS:**
           For EACH action item, provide:
           - Complete description and context
           - Classification: runtime_solution (solved immediately), todo (due <14 days), or potential_rock (strategic/long-term)
           - Specific person assigned (if mentioned) and their role
           - Exact deadline or timeframe mentioned
           - Dependencies or prerequisites
           - Success criteria or deliverables expected
           - Resource requirements or constraints mentioned
           - Priority level (if indicated)
        
        3. **DETAILED PEOPLE & ROLE ANALYSIS:**
           For EACH person mentioned:
           - Their specific involvement and contributions to the discussion
           - Their role, responsibilities, and authority level
           - What they committed to or were assigned
           - Their concerns, suggestions, or decisions made
           - Relationships and interactions with other participants
        
        4. **COMPREHENSIVE TIMELINE & DEADLINE ANALYSIS:**
           - All dates, deadlines, and timeframes with complete context
           - Sequence of activities and dependencies
           - Critical path items and potential bottlenecks
           - Milestone dates and review points
           - Any scheduling conflicts or constraints mentioned
        
        5. **DETAILED DECISIONS & AGREEMENTS:**
           - Specific decisions made with full context
           - Who made the decision and the decision-making process
           - Rationale and supporting arguments
           - Alternatives considered and rejected
           - Implementation approach agreed upon
           - Success metrics and evaluation criteria
        
        6. **COMPREHENSIVE PROJECTS & INITIATIVES:**
           - Complete project/initiative descriptions
           - Scope, objectives, and expected outcomes
           - Resource allocation and team assignments
           - Budget implications or financial considerations
           - Risk factors and mitigation strategies
           - Integration with existing projects or systems
           - Stakeholder impact and communication requirements
        
        7. **BUSINESS CONTEXT & STRATEGIC IMPLICATIONS:**
           - How this segment relates to broader business goals
           - Strategic importance and priority level
           - Competitive implications or market considerations
           - Customer or stakeholder impact
           - Operational or organizational changes required
        
        8. **ISSUES, PROBLEMS & CHALLENGES:**
           - Problems or challenges explicitly discussed
           - Root causes and contributing factors
           - Impact on business operations or goals
           - Proposed solutions and alternatives
           - Resource requirements for resolution
        
        9. **METRICS, KPIs & PERFORMANCE INDICATORS:**
           - Any numbers, percentages, or measurable targets mentioned
           - Performance indicators or success criteria
           - Historical data or trending information
           - Benchmarks or comparison metrics
        
        10. **FOLLOW-UP REQUIREMENTS:**
            - Information needed for next steps
            - Reports or documentation to be prepared
            - Meetings or reviews to be scheduled
            - Communication requirements and stakeholders to inform
        
        IMPORTANT INSTRUCTIONS:
        - Extract ALL actionable items, no matter how small or large
        - Be extremely detailed and specific in your analysis
        - Capture nuanced information and context
        - Don't summarize - provide comprehensive detail
        - Focus on business value and strategic importance
        - Include technical details if they impact business outcomes
        - Identify potential ROCKS (quarterly strategic initiatives) thoroughly
        - Pay special attention to cross-functional dependencies
        - Note any process improvements or efficiency opportunities
        
        Structure your response with clear numbered sections and detailed bullet points for maximum comprehensiveness.
        """
        
        try:
            model_name = os.getenv("OPENAI_MODEL", "gpt-4o")
            response = self.openai_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are an expert business analyst specializing in comprehensive meeting analysis. Provide extremely detailed, thorough analysis with maximum specificity and depth. Extract every actionable item and business insight."},
                    {"role": "user", "content": prompt}
                ],
                
            )
            return {
                "segment_id": segment["segment_id"],
                "analysis": response.choices[0].message.content,
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
        # Create comprehensive ROCKS generation prompt
        prompt = f"""
        # ENHANCED RIZEN Prompting Framework for Comprehensive Meeting Analysis

        ## ROLE & EXPERTISE
        You are a **Master EOS (Entrepreneurial Operating System) Facilitator, Senior Business Analyst, Strategic Meeting Architect, and Organizational Development Expert** with 15+ years of experience in:
        - Comprehensive meeting analysis and synthesis
        - Strategic quarterly planning and ROCKS development
        - Cross-functional team coordination and accountability
        - Long-duration meeting (2-10 hours) content extraction
        - Multi-stakeholder initiative management

        ## CRITICAL CONTEXT
        This is analysis of a COMPREHENSIVE BUSINESS MEETING lasting potentially 2-10 HOURS with {len(segment_analyses)} segments containing rich, detailed discussions. Your task is to extract MAXIMUM VALUE and create COMPREHENSIVE, DETAILED output that captures ALL strategic initiatives, operational improvements, and accountability structures discussed.

        ## CRITICAL PARTICIPANT VALIDATION RULES
        
        **MANDATORY**: You MUST ONLY assign tasks, todos, issues, and rocks to participants who appear in the official participants list below. 
        
        **OFFICIAL PARTICIPANTS LIST:**
        {roles_str}
        
        **VALIDATION REQUIREMENTS:**
        - For "rock_owner", "assigned_to", "raised_by" fields: Use EXACT full names from the participants list above
        - If a person mentioned in the meeting is NOT in the participants list, DO NOT assign any work to them
        - If assignment is unclear, leave the rock/task/todo UNASSIGNED rather than guessing
        - Use "UNASSIGNED" as the value if no clear participant match exists
        
        ## ENHANCED RESPONSIBILITIES

        ### 1. **COMPREHENSIVE Issue Discovery & Deep Structuring**
        - Extract EVERY problem, challenge, bottleneck, or concern discussed
        - Classify each issue with detailed context and business impact
        - Identify root causes and contributing factors
        - Analyze cross-functional dependencies and organizational impact
        - Prioritize issues based on strategic importance and urgency

        ### 2. **DETAILED Categorical Problem-Solving & Solution Architecture**
        For EACH issue identified, determine comprehensive resolution approach:
        - **Runtime Solutions**: Immediate fixes implemented during the meeting with full implementation details
        - **Short-term Tasks (TODOs)**: Specific 14-day deliverables with detailed scope and success criteria
        - **Strategic Quarterly Initiatives (ROCKS)**: Major strategic objectives requiring comprehensive planning

        ### 3. **ADVANCED SMART Rock Creation & Strategic Planning**
        Create MULTIPLE detailed ROCKS for EACH major initiative area:
        - **Department/Function-Specific ROCKS**: Create separate rocks for different teams/functions
        - **Cross-Functional ROCKS**: Strategic initiatives requiring multiple team coordination
        - **Process Improvement ROCKS**: Operational efficiency and system enhancement initiatives
        - **Customer/Market ROCKS**: Customer experience, market expansion, or product development initiatives
        - **Technology/Infrastructure ROCKS**: Technical improvements, system implementations, or digital transformation
        - **Compliance/Risk ROCKS**: Regulatory, security, or risk management initiatives

        Each ROCK must include:
        - **Specific**: Detailed, unambiguous objective with clear scope
        - **Measurable**: Quantifiable success metrics, KPIs, and measurement methods
        - **Achievable**: Realistic given resources and constraints mentioned
        - **Relevant**: Clear business impact and strategic alignment
        - **Time-bound**: Specific quarterly timeline with milestone checkpoints

        ### 4. **COMPREHENSIVE Weekly Milestone Planning**
        For each ROCK, create DETAILED weekly breakdown:
        - Week-by-week progression with specific deliverables
        - Resource allocation and team member assignments
        - Dependency management and critical path identification
        - Risk mitigation checkpoints and contingency planning
        - Progress measurement and review mechanisms

        ### 5. **DETAILED Summary Architecture & Strategic Communication**
        Create COMPREHENSIVE summaries including:
        - **Executive Overview**: High-level strategic themes and decisions
        - **Departmental Impact Analysis**: How each function is affected
        - **Resource Allocation Summary**: Human, financial, and technical resources required
        - **Timeline and Dependency Matrix**: Critical path and interdependencies
        - **Risk Assessment**: Potential challenges and mitigation strategies

        ## ENHANCED INPUT ANALYSIS
        
        COMPREHENSIVE MEETING ANALYTICS:
        - **Total Segments Analyzed**: {len(segment_analyses)} (indicating comprehensive, detailed meeting)
        - **Unique Participants**: {list(all_people)}
        - **Organizations Involved**: {list(all_organizations)}
        - **Timeline References**: {list(all_dates)}
        - **Total Action Items Identified**: {len(total_action_items)}
        - **Strategic Planning Period**: {num_weeks} weeks
        
        **AGGREGATED STRATEGIC INSIGHTS**:
        - Strategic Initiatives Identified: {aggregated_insights['context_summary']['total_strategic_initiatives']}
        - Operational Improvements: {aggregated_insights['context_summary']['total_operational_improvements']}
        - Technology Initiatives: {aggregated_insights['context_summary']['total_technology_initiatives']}
        - Cross-Functional Projects: {aggregated_insights['context_summary']['total_cross_functional_projects']}
        - Unique Stakeholders: {aggregated_insights['context_summary']['unique_stakeholders']}
        - Complexity Indicators: {aggregated_insights['context_summary']['complexity_indicators']}
        
        **PARTICIPANT ROLES & RESPONSIBILITIES**:
        {roles_str}

        **COMPREHENSIVE SEGMENT ANALYSES**:
        {analyses_text}
        
        **STRATEGIC CONTEXT AGGREGATION**:
        Strategic Initiatives: {len(aggregated_insights['strategic_initiatives'])} major strategic tracks identified
        Operational Improvements: {len(aggregated_insights['operational_improvements'])} efficiency opportunities
        Technology Initiatives: {len(aggregated_insights['technology_initiatives'])} technical projects
        Cross-Functional Projects: {len(aggregated_insights['cross_functional_projects'])} coordination requirements

        ## ENHANCED OUTPUT REQUIREMENTS

        ### CRITICAL INSTRUCTIONS FOR MAXIMUM DETAIL:
        1. **GENERATE MULTIPLE ROCKS PER PERSON**: Each participant should have 2-4 strategic initiatives
        2. **CREATE DEPARTMENT-SPECIFIC ROCKS**: Separate rocks for different functional areas
        3. **DEVELOP CROSS-FUNCTIONAL ROCKS**: Strategic initiatives requiring coordination
        4. **INCLUDE PROCESS IMPROVEMENT ROCKS**: Operational efficiency initiatives
        5. **ADD CUSTOMER/MARKET ROCKS**: External-facing strategic objectives
        6. **INCORPORATE TECHNOLOGY ROCKS**: System, tool, or infrastructure improvements
        7. **ESTABLISH COMPLIANCE/GOVERNANCE ROCKS**: Risk management and regulatory initiatives

        ### DETAILED JSON STRUCTURE REQUIREMENTS:
        {{
            "session_summary": {{
                "meeting_overview": "Comprehensive 3-4 sentence overview covering all major themes, strategic decisions, and organizational impact",
                "strategic_themes": "Detailed analysis of strategic direction, priorities, and business transformation initiatives discussed",
                "departmental_impact": "Comprehensive analysis of how different departments/functions are affected by meeting outcomes",
                "issues_summary": "Detailed categorization and analysis of all problems, challenges, and improvement opportunities raised",
                "todos_summary": "Comprehensive overview of short-term deliverables, immediate actions, and 14-day commitments",
                "rocks_summary": "Strategic synthesis of quarterly initiatives, their business impact, and organizational transformation expected",
                "resource_implications": "Analysis of human, financial, and technical resources required for successful implementation",
                "success_metrics": "Key performance indicators and measurement criteria for tracking progress and success"
            }},
            "issues": [
                // GENERATE 8-15 DETAILED ISSUES covering all aspects discussed
                {{
                    "issue_title": "Specific, descriptive title capturing the core problem",
                    "description": "Comprehensive 2-3 sentence description including context, impact, and urgency",
                    "business_impact": "Detailed analysis of how this issue affects operations, customers, or strategic goals",
                    "root_causes": "Identified underlying causes and contributing factors",
                    "raised_by": "EXACT Full Name from participants list ONLY - use 'UNASSIGNED' if person not in list",
                    "supporting_stakeholders": ["Names of others who discussed or supported this issue"],
                    "discussion_notes": "Detailed summary of key discussion points, alternatives considered, and decisions made",
                    "urgency_level": "High | Medium | Low",
                    "complexity_level": "High | Medium | Low",
                    "resource_requirements": "Analysis of resources needed for resolution",
                    "linked_solution_type": "rock | todo | runtime_solution",
                    "linked_solution_ref": "Exact title of the related solution"
                }}
            ],
            "runtime_solutions": [
                // GENERATE 5-10 IMMEDIATE SOLUTIONS that were resolved during the meeting
                {{
                    "solution_title": "Specific action taken and resolved during meeting with context",
                    "description": "Detailed explanation of the solution, implementation approach, and immediate outcomes",
                    "problem_addressed": "Reference to the specific issue this solution resolves",
                    "implementation_details": "Step-by-step approach taken during the meeting",
                    "assigned_to": "EXACT Full Name from participants list ONLY - use 'UNASSIGNED' if person not in list",
                    "designation": "Exact job title from participants list",
                    "deadline": "YYYY-MM-DD (realistic date based on discussion)",
                    "success_criteria": "Specific measurable outcomes expected",
                    "resources_utilized": "Resources allocated or utilized for this solution"
                }}
            ],
            "todos": [
                // GENERATE 10-20 DETAILED SHORT-TERM TASKS with comprehensive scope
                {{
                    "task_title": "Specific, actionable short-term deliverable with clear scope",
                    "description": "Comprehensive 2-3 sentence description including context, requirements, and expected deliverables",
                    "scope_details": "Detailed breakdown of what is included and excluded from this task",
                    "assigned_to": "EXACT Full Name from participants list ONLY - use 'UNASSIGNED' if person not in list",
                    "designation": "Exact job title from participants list",
                    "due_date": "YYYY-MM-DD (within 14 days)",
                    "priority_level": "High | Medium | Low",
                    "estimated_effort": "Estimated hours or days required",
                    "dependencies": ["List of prerequisites or dependencies"],
                    "deliverables": ["Specific outputs or deliverables expected"],
                    "success_criteria": "Measurable criteria for task completion",
                    "linked_issue": "Title of related issue from issues array",
                    "review_checkpoints": ["Interim review points or milestones"]
                }}
            ],
            "rocks": [
                // GENERATE 15-25 COMPREHENSIVE STRATEGIC ROCKS covering all participants and initiatives
                {{
                    "rock_owner": "EXACT Full Name from participants list ONLY - use 'UNASSIGNED' if person not in list",
                    "designation": "Exact job title from participants list",
                    "functional_area": "Department or functional area this rock impacts",
                    "strategic_category": "Technology | Process | Customer | Market | Compliance | Operations | Finance | HR",
                    "smart_rock": "Comprehensive, specific, measurable, achievable, relevant, time-bound quarterly objective with quantifiable outcomes",
                    "business_justification": "Detailed explanation of why this rock is strategically important and its expected business impact",
                    "success_metrics": [
                        "Specific KPI 1 with target value",
                        "Specific KPI 2 with target value",
                        "Specific KPI 3 with target value"
                    ],
                    "resource_requirements": {{
                        "human_resources": "Team members and time allocation required",
                        "financial_budget": "Estimated budget or financial resources needed",
                        "technical_resources": "Systems, tools, or technology required",
                        "external_resources": "Vendors, contractors, or external support needed"
                    }},
                    "milestones": [
                        // GENERATE DETAILED WEEKLY BREAKDOWN FOR ALL {num_weeks} WEEKS
                        // Example format for each week:
                        {{
                            "week": 1,
                            "milestones": [
                                "Specific milestone 1 with clear deliverable and success criteria",
                                "Specific milestone 2 with measurable outcome",
                                "Specific milestone 3 with resource allocation details"
                            ],
                            "key_activities": ["Detailed activity 1", "Detailed activity 2"],
                            "deliverables": ["Specific deliverable 1", "Specific deliverable 2"],
                            "success_criteria": "Measurable criteria for week completion"
                        }},
                        {{
                            "week": 2,
                            "milestone": "Single comprehensive milestone with detailed scope and expected outcome",
                            "key_activities": ["Detailed activity 1", "Detailed activity 2"],
                            "deliverables": ["Specific deliverable"],
                            "success_criteria": "Measurable criteria for week completion"
                        }}
                        // IMPORTANT: YOU MUST GENERATE MILESTONES FOR ALL {num_weeks} WEEKS (1 through {num_weeks})
                        // Do not stop at week 2 - continue generating milestones for weeks 3, 4, 5... up to week {num_weeks}
                    ],
                    "dependencies": [
                        "Detailed dependency 1 with timeline impact",
                        "Detailed dependency 2 with risk assessment"
                    ],
                    "risk_factors": [
                        "Specific risk 1 with likelihood and impact assessment",
                        "Specific risk 2 with mitigation strategy"
                    ],
                    "linked_issues": [
                        "Exact title of related issue 1",
                        "Exact title of related issue 2"
                    ],
                    "collaboration_requirements": ["Cross-functional coordination needs"],
                    "review_checkpoints": ["Weekly review", "Bi-weekly stakeholder update", "Monthly strategic review"]
                }}
            ],
            "strategic_initiatives": {{
                "cross_functional_projects": [
                    // Projects requiring multiple departments
                    {{
                        "project_name": "Comprehensive project title",
                        "description": "Detailed project scope and objectives",
                        "involved_departments": ["Department 1", "Department 2"],
                        "project_leads": ["Lead 1", "Lead 2"],
                        "timeline": "Project duration and key milestones",
                        "expected_outcomes": ["Outcome 1", "Outcome 2"]
                    }}
                ],
                "process_improvements": [
                    // Operational efficiency initiatives
                    {{
                        "improvement_area": "Specific process or area for improvement",
                        "current_state": "Description of current situation",
                        "target_state": "Desired future state",
                        "implementation_approach": "Step-by-step improvement plan",
                        "expected_benefits": ["Benefit 1", "Benefit 2"]
                    }}
                ],
                "technology_initiatives": [
                    // Technical improvements and implementations
                    {{
                        "initiative_name": "Technology project or implementation",
                        "technical_scope": "Detailed technical requirements",
                        "business_justification": "Why this technology initiative is needed",
                        "implementation_timeline": "Technical implementation schedule",
                        "expected_roi": "Return on investment expectations"
                    }}
                ]
            }},
            "compliance_log": {{
                "transcription_tool": "Python Speech Recognition",
                "genai_model": "OpenAI {os.getenv('OPENAI_MODEL', 'gpt-4o')}",
                "facilitator_review_timestamp": "{datetime.now().isoformat()}",
                "data_storage_platform": "Local Processing",
                "processing_pipeline_version": "2.0",
                "analysis_depth": "Comprehensive",
                "meeting_duration_estimate": "2-10 hours based on segment count",
                "generation_attempts": "<GEN_ATTEMPTS>"
            }}
        }}

        ## CRITICAL SUCCESS FACTORS:
        1. **MAXIMUM EXTRACTION**: Extract every actionable item, strategic initiative, and business opportunity
        2. **COMPREHENSIVE ROCKS**: Generate 15-25 detailed ROCKS covering all participants and functional areas
        3. **DETAILED MILESTONES**: Provide specific, measurable weekly milestones for each ROCK FOR ALL {num_weeks} WEEKS
        4. **CROSS-FUNCTIONAL COVERAGE**: Ensure all departments and functions have strategic initiatives
        5. **BUSINESS IMPACT FOCUS**: Emphasize strategic value and measurable business outcomes
        6. **RESOURCE SPECIFICITY**: Detail human, financial, and technical resource requirements
        7. **RISK CONSIDERATION**: Include risk assessment and mitigation strategies
        8. **ACCOUNTABILITY STRUCTURE**: Clear ownership and review mechanisms

        ## MILESTONE GENERATION REQUIREMENTS:
        - CRITICAL: Generate milestones for ALL {num_weeks} weeks (not just 1-2 weeks)
        - Each ROCK must have detailed weekly milestones from week 1 to week {num_weeks}
        - Do not truncate or limit the milestone generation

        ## FINAL VALIDATION REQUIREMENTS:
        - Every participant from the CSV should have multiple ROCKS assigned
        - All strategic themes from the meeting should be represented in ROCKS
        - Each ROCK should have quantifiable success metrics
        - Weekly milestones should be specific and actionable
        - JSON structure must be complete and valid
        - Response should reflect the depth and comprehensiveness of a long strategic meeting

        Generate the most comprehensive, detailed, and strategic response possible that maximizes the value extracted from this extensive meeting content.
        """
        # Retry loop for JSON generation
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Generating ROCKS from segment analyses (attempt {attempt + 1}/{max_retries + 1})...")
                model_name = os.getenv("OPENAI_MODEL", "gpt-4o")
                response = self.openai_client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are a master EOS facilitator and business analyst creating comprehensive ROCKS (quarterly goals) from extensive meeting analyses. Generate maximum detail and extract every strategic initiative. Return only valid JSON with comprehensive detail."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    max_tokens=16000
                )
                response_content = response.choices[0].message.content or ""
                json_response = self._handle_large_response(response_content.strip())
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

            # Step 2: Semantic Tokenization (transcript_json is already in the correct structure)
            semantic_data = self.semantic_tokenization(transcript_json)
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
            logger.error(f"Pipeline (from transcript) failed: {e}")
            return {"error": str(e), "status": "failed"}

# Convenience function for easy usage
async def run_pipeline_for_audio(audio_file: str, num_weeks: int, quarter_id: str, participants: list, admin_id: str = "default_admin") -> Dict[str, Any]:
    """Convenience function to run pipeline for a given audio file"""
    pipeline = PipelineService(admin_id)
    return await pipeline.run_pipeline(audio_file, num_weeks, quarter_id, participants)

async def run_pipeline_for_transcript(transcript_json: dict, num_weeks: int, quarter_id: str, participants: list, admin_id: str = "default_admin") -> dict:
    """
    Convenience function to run pipeline for a given transcript JSON
    """
    pipeline = PipelineService(admin_id)
    return await pipeline.run_pipeline_for_transcript(transcript_json, num_weeks, quarter_id, participants)
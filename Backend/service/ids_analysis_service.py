from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID, uuid4
from datetime import datetime, date, timedelta
import re
import json
from models.issue import Issue
from models.solution import Solution, SolutionTimeline
from models.milestone import Milestone
from models.time_slot import TimeSlot
from .issue_service import IssueService
from .solution_service import SolutionService
from .milestone_service import MilestoneService
from .time_slot_service import TimeSlotService

class IDSAnalysisService:
    """
    Service for analyzing meeting transcripts using IDS (Issues, Decisions, Solutions) methodology
    """
    
    @staticmethod
    async def analyze_transcript_for_ids(
        transcript_data: Dict[str, Any],
        meeting_id: UUID,
        meeting_type: str
    ) -> Dict[str, Any]:
        """
        Comprehensive IDS analysis of meeting transcript
        """
        
        # Extract raw transcript and segments
        raw_transcript = transcript_data.get("full_transcript", "")
        segments = transcript_data.get("segments", [])
        
        # Initialize analysis results
        ids_analysis = {
            "issues": [],
            "solutions": {
                "runtime_solutions": [],
                "to_dos": [],
                "rocks": []
            },
            "open_issues": [],
            "time_slot_analysis": []
        }
        
        # Step 1: Extract time slots with timestamps
        time_slots = await IDSAnalysisService._extract_time_slots(segments, meeting_id)
        ids_analysis["time_slot_analysis"] = [slot.model_dump() for slot in time_slots]
        
        # Step 2: Identify issues from transcript
        issues = await IDSAnalysisService._identify_issues(segments, meeting_id)
        ids_analysis["issues"] = [issue.model_dump() for issue in issues]
        
        # Step 3: Identify solutions and classify by timeframe
        solutions = await IDSAnalysisService._identify_solutions(segments, meeting_id, issues)
        
        # Classify solutions by type
        for solution in solutions:
            timeframe_days = solution.timeline.duration_days
            
            if timeframe_days == 0:  # Runtime solutions
                ids_analysis["solutions"]["runtime_solutions"].append(solution.model_dump())
            elif 1 <= timeframe_days <= 14:  # To-dos
                ids_analysis["solutions"]["to_dos"].append(solution.model_dump())
            elif 15 <= timeframe_days <= 90:  # Rocks
                ids_analysis["solutions"]["rocks"].append(solution.model_dump())
        
        # Step 4: Identify unresolved issues
        resolved_issue_ids = {sol.issue_reference for sol in solutions if sol.issue_reference}
        open_issues = [issue for issue in issues if issue.issue_id not in resolved_issue_ids]
        ids_analysis["open_issues"] = [issue.model_dump() for issue in open_issues]
        
        # Step 5: Create milestones for rocks and complex to-dos
        await IDSAnalysisService._create_milestones(solutions, meeting_id)
        
        # Step 6: Generate summaries
        ids_analysis["summaries"] = await IDSAnalysisService._generate_summaries(
            issues, solutions, meeting_type
        )
        
        return ids_analysis

    @staticmethod
    async def _extract_time_slots(segments: List[Dict], meeting_id: UUID) -> List[TimeSlot]:
        """Extract time slots from transcript segments"""
        time_slots = []
        
        # Group segments into meaningful time slots (5-10 minute chunks)
        slot_duration = 300  # 5 minutes in seconds
        current_slot_start = 0
        current_slot_content = []
        
        for i, segment in enumerate(segments):
            timestamp = segment.get("timestamp", "00:00:00")
            text = segment.get("text", "")
            speaker = segment.get("speaker", "Unknown")
            
            # Convert timestamp to seconds
            time_parts = timestamp.split(":")
            timestamp_seconds = int(time_parts[0]) * 3600 + int(time_parts[1]) * 60 + int(time_parts[2])
            
            # Check if we should create a new time slot
            if timestamp_seconds - current_slot_start >= slot_duration or i == len(segments) - 1:
                if current_slot_content:
                    # Create time slot
                    slot = await IDSAnalysisService._create_time_slot_from_content(
                        current_slot_content, meeting_id, current_slot_start, timestamp_seconds
                    )
                    if slot:
                        time_slots.append(slot)
                
                # Reset for next slot
                current_slot_start = timestamp_seconds
                current_slot_content = []
            
            current_slot_content.append({
                "timestamp": timestamp,
                "speaker": speaker,
                "text": text
            })
        
        return time_slots

    @staticmethod
    async def _create_time_slot_from_content(
        content: List[Dict], 
        meeting_id: UUID, 
        start_seconds: int, 
        end_seconds: int
    ) -> Optional[TimeSlot]:
        """Create a time slot from content segments"""
        
        if not content:
            return None
        
        # Extract information from content
        combined_text = " ".join([item["text"] for item in content])
        participants = list(set([item["speaker"] for item in content if item["speaker"] != "Unknown"]))
        
        # Analyze content to determine topic and category
        topic = IDSAnalysisService._extract_topic(combined_text)
        category = IDSAnalysisService._classify_discussion_category(combined_text)
        key_points = IDSAnalysisService._extract_key_points(combined_text)
        outcomes = IDSAnalysisService._extract_outcomes(combined_text)
        
        # Convert seconds to timestamp format
        start_time = IDSAnalysisService._seconds_to_timestamp(start_seconds)
        end_time = IDSAnalysisService._seconds_to_timestamp(end_seconds)
        
        time_slot_data = {
            "meeting_id": meeting_id,
            "start_time": start_time,
            "end_time": end_time,
            "duration_seconds": end_seconds - start_seconds,
            "topic": topic,
            "category": category,
            "participants": participants,
            "key_points": key_points,
            "outcomes": outcomes,
            "transcript_segment": combined_text[:1000]  # Limit length
        }
        
        return TimeSlot(**time_slot_data)

    @staticmethod
    async def _identify_issues(segments: List[Dict], meeting_id: UUID) -> List[Issue]:
        """Identify issues from transcript segments"""
        issues = []
        
        # Keywords that typically indicate issues
        issue_keywords = [
            "problem", "issue", "challenge", "difficulty", "obstacle", 
            "bottleneck", "blocking", "stuck", "failure", "error",
            "concern", "risk", "threat", "shortage", "lack", "missing"
        ]
        
        for segment in segments:
            text = segment.get("text", "").lower()
            timestamp = segment.get("timestamp", "00:00:00")
            speaker = segment.get("speaker", "Unknown")
            
            # Check if segment contains issue indicators
            if any(keyword in text for keyword in issue_keywords):
                issue = await IDSAnalysisService._extract_issue_from_segment(
                    segment, meeting_id, timestamp, speaker
                )
                if issue:
                    issues.append(issue)
        
        return issues

    @staticmethod
    async def _extract_issue_from_segment(
        segment: Dict, 
        meeting_id: UUID, 
        timestamp: str, 
        speaker: str
    ) -> Optional[Issue]:
        """Extract issue details from a segment"""
        
        text = segment.get("text", "")
        
        # Extract title (first sentence or key phrase)
        sentences = text.split(".")
        title = sentences[0].strip() if sentences else text[:100]
        
        # Classify issue category
        category = IDSAnalysisService._classify_issue_category(text)
        
        # Determine priority
        priority = IDSAnalysisService._determine_issue_priority(text)
        
        # Generate summary
        summary = IDSAnalysisService._generate_issue_summary(text, category)
        
        issue_data = {
            "meeting_id": meeting_id,
            "title": title,
            "description": text,
            "category": category,
            "priority": priority,
            "mentioned_by": speaker,
            "timestamp": timestamp,
            "summary": summary,
            "status": "open"
        }
        
        return Issue(**issue_data)

    @staticmethod
    async def _identify_solutions(
        segments: List[Dict], 
        meeting_id: UUID, 
        issues: List[Issue]
    ) -> List[Solution]:
        """Identify solutions from transcript segments"""
        solutions = []
        
        # Keywords that typically indicate solutions
        solution_keywords = [
            "solution", "resolve", "fix", "implement", "deploy", "create",
            "build", "develop", "establish", "setup", "configure", "assign",
            "allocate", "hire", "purchase", "upgrade", "migrate", "optimize"
        ]
        
        for segment in segments:
            text = segment.get("text", "").lower()
            timestamp = segment.get("timestamp", "00:00:00")
            speaker = segment.get("speaker", "Unknown")
            
            # Check if segment contains solution indicators
            if any(keyword in text for keyword in solution_keywords):
                solution = await IDSAnalysisService._extract_solution_from_segment(
                    segment, meeting_id, timestamp, speaker, issues
                )
                if solution:
                    solutions.append(solution)
        
        return solutions

    @staticmethod
    async def _extract_solution_from_segment(
        segment: Dict, 
        meeting_id: UUID, 
        timestamp: str, 
        speaker: str,
        issues: List[Issue]
    ) -> Optional[Solution]:
        """Extract solution details from a segment"""
        
        text = segment.get("text", "")
        
        # Extract title (first sentence or key phrase)
        sentences = text.split(".")
        title = sentences[0].strip() if sentences else text[:100]
        
        # Determine timeframe and solution type
        timeframe_days = IDSAnalysisService._extract_timeframe(text)
        solution_type = IDSAnalysisService._classify_solution_type(timeframe_days)
        
        # Extract owner/assignee
        owner = IDSAnalysisService._extract_owner(text, speaker)
        
        # Create timeline
        start_date = date.today()
        end_date = start_date + timedelta(days=timeframe_days)
        timeline = SolutionTimeline(
            start_date=start_date,
            end_date=end_date,
            duration_days=timeframe_days
        )
        
        # Try to match with an issue
        issue_reference = IDSAnalysisService._match_solution_to_issue(text, issues)
        
        # Generate summary
        summary = IDSAnalysisService._generate_solution_summary(text, solution_type)
        
        solution_data = {
            "solution_type": solution_type,
            "meeting_id": meeting_id,
            "issue_reference": issue_reference,
            "title": title,
            "description": text,
            "owner": owner,
            "timeline": timeline.model_dump(),
            "summary": summary,
            "mentioned_by": speaker,
            "timestamp": timestamp
        }
        
        # Add SMART objective for rocks
        if solution_type == "rock":
            solution_data["smart_objective"] = IDSAnalysisService._generate_smart_objective(text, title)
            solution_data["measurable_success"] = IDSAnalysisService._generate_measurable_success(text)
        
        return Solution(**solution_data)

    @staticmethod
    async def _create_milestones(solutions: List[Solution], meeting_id: UUID) -> List[Milestone]:
        """Create milestones for rocks and complex to-dos"""
        milestones = []
        
        for solution in solutions:
            if solution.solution_type in ["rock", "todo"] and solution.timeline.duration_days > 7:
                # Create weekly milestones
                weekly_milestones = await IDSAnalysisService._create_weekly_milestones(
                    solution, meeting_id
                )
                milestones.extend(weekly_milestones)
        
        return milestones

    @staticmethod
    async def _create_weekly_milestones(solution: Solution, meeting_id: UUID) -> List[Milestone]:
        """Create weekly milestones for a solution"""
        milestones = []
        weeks = max(1, solution.timeline.duration_days // 7)
        
        for week in range(1, weeks + 1):
            milestone_data = {
                "parent_id": solution.solution_id,
                "parent_type": "solution",
                "title": f"Week {week} milestone for {solution.title}",
                "description": f"Weekly milestone {week} of {weeks} for {solution.title}",
                "due_date": solution.timeline.start_date + timedelta(weeks=week),
                "week_number": week,
                "summary": f"Week {week} milestone to progress towards: {solution.title}",
                "meeting_reference": meeting_id
            }
            
            milestone = Milestone(**milestone_data)
            milestones.append(milestone)
            
            # Add milestone reference to solution
            if milestone.milestone_id not in solution.milestones:
                solution.milestones.append(milestone.milestone_id)
        
        return milestones

    @staticmethod
    async def _generate_summaries(
        issues: List[Issue], 
        solutions: List[Solution], 
        meeting_type: str
    ) -> Dict[str, str]:
        """Generate summaries for IDS components"""
        
        return {
            "issues_summary": IDSAnalysisService._summarize_issues(issues),
            "solutions_summary": IDSAnalysisService._summarize_solutions(solutions),
            "meeting_summary": IDSAnalysisService._generate_meeting_summary(issues, solutions, meeting_type)
        }

    # Helper methods for classification and extraction
    
    @staticmethod
    def _classify_issue_category(text: str) -> str:
        """Classify issue into categories"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["resource", "capacity", "budget", "funding", "staff"]):
            return "resource"
        elif any(word in text_lower for word in ["technical", "system", "software", "hardware", "bug"]):
            return "technical"
        elif any(word in text_lower for word in ["strategy", "vision", "goal", "objective", "plan"]):
            return "strategic"
        elif any(word in text_lower for word in ["process", "workflow", "procedure", "operation"]):
            return "operational"
        elif any(word in text_lower for word in ["compliance", "regulation", "policy", "legal"]):
            return "compliance"
        elif any(word in text_lower for word in ["market", "customer", "competition", "sales"]):
            return "market"
        elif any(word in text_lower for word in ["team", "personnel", "hiring", "training"]):
            return "personnel"
        else:
            return "operational"

    @staticmethod
    def _determine_issue_priority(text: str) -> str:
        """Determine issue priority from text"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["critical", "urgent", "emergency", "blocking", "immediate"]):
            return "critical"
        elif any(word in text_lower for word in ["high", "important", "priority", "asap"]):
            return "high"
        elif any(word in text_lower for word in ["low", "minor", "later", "eventually"]):
            return "low"
        else:
            return "medium"

    @staticmethod
    def _extract_timeframe(text: str) -> int:
        """Extract timeframe in days from text"""
        text_lower = text.lower()
        
        # Look for specific timeframes
        if any(word in text_lower for word in ["immediate", "now", "today", "asap"]):
            return 0
        elif any(word in text_lower for word in ["week", "weekly"]):
            return 7
        elif "2 week" in text_lower or "two week" in text_lower:
            return 14
        elif any(word in text_lower for word in ["month", "monthly"]):
            return 30
        elif any(word in text_lower for word in ["quarter", "quarterly"]):
            return 90
        elif any(word in text_lower for word in ["year", "annual"]):
            return 365
        
        # Look for numeric patterns
        import re
        day_pattern = r'(\d+)\s*day'
        week_pattern = r'(\d+)\s*week'
        month_pattern = r'(\d+)\s*month'
        
        day_match = re.search(day_pattern, text_lower)
        if day_match:
            return int(day_match.group(1))
        
        week_match = re.search(week_pattern, text_lower)
        if week_match:
            return int(week_match.group(1)) * 7
        
        month_match = re.search(month_pattern, text_lower)
        if month_match:
            return int(month_match.group(1)) * 30
        
        # Default to 30 days if no timeframe specified
        return 30

    @staticmethod
    def _classify_solution_type(timeframe_days: int) -> str:
        """Classify solution type based on timeframe"""
        if timeframe_days == 0:
            return "runtime"
        elif 1 <= timeframe_days <= 14:
            return "todo"
        elif 15 <= timeframe_days <= 90:
            return "rock"
        else:
            return "rock"  # Long-term solutions are also rocks

    @staticmethod
    def _extract_owner(text: str, speaker: str) -> str:
        """Extract owner/assignee from text"""
        # Look for assignment patterns
        assignment_patterns = [
            r"assign(?:ed)?\s+to\s+([A-Za-z\s]+)",
            r"([A-Za-z\s]+)\s+will\s+(?:handle|do|work|take)",
            r"([A-Za-z\s]+)\s+team",
            r"([A-Za-z\s]+)\s+responsible"
        ]
        
        for pattern in assignment_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Default to speaker if no specific assignment found
        return speaker

    @staticmethod
    def _match_solution_to_issue(text: str, issues: List[Issue]) -> Optional[UUID]:
        """Try to match solution with an issue based on content similarity"""
        # Simple keyword matching approach
        solution_keywords = set(text.lower().split())
        
        best_match = None
        best_score = 0
        
        for issue in issues:
            issue_keywords = set(issue.description.lower().split())
            common_keywords = solution_keywords.intersection(issue_keywords)
            score = len(common_keywords)
            
            if score > best_score and score >= 3:  # Minimum 3 common words
                best_score = score
                best_match = issue.issue_id
        
        return best_match

    @staticmethod
    def _extract_topic(text: str) -> str:
        """Extract main topic from text"""
        # Simple approach: use first few words or key phrases
        sentences = text.split(".")
        first_sentence = sentences[0].strip() if sentences else text
        
        # Limit length and clean up
        topic = first_sentence[:100].strip()
        return topic if topic else "General discussion"

    @staticmethod
    def _classify_discussion_category(text: str) -> str:
        """Classify discussion category"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["problem", "issue", "challenge", "concern"]):
            return "issues"
        elif any(word in text_lower for word in ["solution", "resolve", "fix", "implement"]):
            return "solutions"
        elif any(word in text_lower for word in ["decide", "decision", "agree", "approve"]):
            return "decisions"
        elif any(word in text_lower for word in ["plan", "schedule", "timeline", "roadmap"]):
            return "planning"
        elif any(word in text_lower for word in ["review", "status", "progress", "update"]):
            return "review"
        else:
            return "discussion"

    @staticmethod
    def _extract_key_points(text: str) -> List[str]:
        """Extract key discussion points"""
        # Split by sentences and filter meaningful ones
        sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 20]
        return sentences[:5]  # Limit to top 5 key points

    @staticmethod
    def _extract_outcomes(text: str) -> List[str]:
        """Extract outcomes from discussion"""
        outcome_keywords = ["result", "outcome", "conclusion", "decision", "agreement", "resolution"]
        outcomes = []
        
        sentences = text.split(".")
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in outcome_keywords):
                outcomes.append(sentence.strip())
        
        return outcomes[:3]  # Limit to top 3 outcomes

    @staticmethod
    def _seconds_to_timestamp(seconds: int) -> str:
        """Convert seconds to HH:MM:SS format"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    @staticmethod
    def _generate_smart_objective(text: str, title: str) -> str:
        """Generate SMART objective for rocks"""
        # This is a simplified version - in practice, this would use more sophisticated NLP
        return f"Achieve {title} with measurable results and clear timeline as discussed in meeting"

    @staticmethod
    def _generate_measurable_success(text: str) -> str:
        """Generate measurable success criteria"""
        # Look for numeric indicators or percentages
        import re
        numeric_patterns = re.findall(r'\d+%|\d+\s*(?:percent|people|days|weeks|months)', text.lower())
        
        if numeric_patterns:
            return f"Success measured by: {', '.join(numeric_patterns)}"
        else:
            return "Success criteria to be defined with specific metrics and benchmarks"

    @staticmethod
    def _generate_issue_summary(text: str, category: str) -> str:
        """Generate summary for an issue"""
        return f"{category.title()} issue identified: {text[:150]}..."

    @staticmethod
    def _generate_solution_summary(text: str, solution_type: str) -> str:
        """Generate summary for a solution"""
        return f"{solution_type.title()} solution proposed: {text[:150]}..."

    @staticmethod
    def _summarize_issues(issues: List[Issue]) -> str:
        """Generate summary of all issues"""
        if not issues:
            return "No issues identified in this meeting"
        
        category_counts = {}
        priority_counts = {}
        
        for issue in issues:
            category_counts[issue.category] = category_counts.get(issue.category, 0) + 1
            priority_counts[issue.priority] = priority_counts.get(issue.priority, 0) + 1
        
        summary = f"Identified {len(issues)} issues: "
        summary += ", ".join([f"{count} {cat}" for cat, count in category_counts.items()])
        summary += f". Priority breakdown: {dict(priority_counts)}"
        
        return summary

    @staticmethod
    def _summarize_solutions(solutions: List[Solution]) -> str:
        """Generate summary of all solutions"""
        if not solutions:
            return "No solutions proposed in this meeting"
        
        type_counts = {}
        for solution in solutions:
            type_counts[solution.solution_type] = type_counts.get(solution.solution_type, 0) + 1
        
        summary = f"Proposed {len(solutions)} solutions: "
        summary += ", ".join([f"{count} {sol_type}" for sol_type, count in type_counts.items()])
        
        return summary

    @staticmethod
    def _generate_meeting_summary(issues: List[Issue], solutions: List[Solution], meeting_type: str) -> str:
        """Generate overall meeting summary"""
        summary = f"{meeting_type.title()} meeting completed with "
        summary += f"{len(issues)} issues identified and {len(solutions)} solutions proposed. "
        
        if solutions:
            solution_ratio = len(solutions) / len(issues) if issues else 0
            if solution_ratio >= 1:
                summary += "Good problem-solving ratio achieved."
            else:
                summary += "Additional solution development may be needed."
        
        return summary

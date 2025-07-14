#!/usr/bin/env python3
"""
Test script for the enhanced milestone optimization service
Demonstrates the timeline compression and milestone redistribution functionality
"""

import json
import sys
import os
from typing import List, Dict

# Add the current directory to the path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.rock import RockPayload
from service.edit_milestones_service import (
    process_custom_rock_payload,
    analyze_milestone_distribution,
    distribute_milestones_to_weeks,
    calculate_compression_factor
)

def create_sample_rock_data() -> Dict:
    """Create sample rock data for testing"""
    return {
        "rock_id": "rock_123",
        "quarter_id": "q1_2024", 
        "rock_name": "Launch New Product Feature",
        "milestones": [
            "Market research and competitor analysis",
            "Define product requirements and specifications", 
            "Create wireframes and user flow diagrams",
            "Design UI mockups and prototypes",
            "Set up development environment and tools",
            "Implement core functionality - user authentication",
            "Implement core functionality - data management",
            "Implement core functionality - API integration",
            "Design and implement database schema",
            "Create unit tests for core components",
            "Integrate frontend with backend APIs",
            "Implement user interface components",
            "Add data validation and error handling",
            "Perform initial testing and bug fixes",
            "Conduct code review and optimization",
            "Create documentation and user guides",
            "Set up staging environment for testing",
            "Perform integration testing",
            "Conduct user acceptance testing",
            "Address feedback and final adjustments",
            "Prepare production deployment scripts",
            "Deploy to production environment",
            "Monitor system performance and stability",
            "Collect user feedback and analytics"
        ],
        "weeks": 9,  # Target: compress from 12 weeks to 9 weeks
        "duration": "2024-01-01 to 2024-03-03",
        "milestone_no": 20,  # Target: reduce from 24 to 20 milestones
        "original_weeks": 12  # Original timeline was 12 weeks
    }

def test_milestone_analysis():
    """Test milestone distribution analysis"""
    print("🔍 Testing Milestone Analysis...")
    
    sample_data = create_sample_rock_data()
    milestones = sample_data["milestones"]
    original_weeks = sample_data.get("original_weeks", 12)
    
    analysis = analyze_milestone_distribution(milestones, original_weeks)
    
    print(f"📊 Analysis Results:")
    print(f"   Total milestones: {analysis['total_milestones']}")
    print(f"   Average per week: {analysis['avg_per_week']:.2f}")
    print(f"   Distribution: {analysis['distribution']}")
    print()

def test_compression_calculation():
    """Test timeline compression metrics"""
    print("⏱️ Testing Compression Calculation...")
    
    original_weeks = 12
    new_weeks = 9
    
    metrics = calculate_compression_factor(original_weeks, new_weeks)
    
    print(f"📈 Compression Metrics:")
    print(f"   Compression ratio: {metrics['compression_ratio']}")
    print(f"   Time saved: {metrics['time_saved']} weeks")
    print(f"   Intensity increase: {metrics['intensity_increase']}%")
    print()

def test_milestone_distribution():
    """Test milestone distribution across weeks"""
    print("📅 Testing Milestone Distribution...")
    
    sample_milestones = [
        "Milestone 1", "Milestone 2", "Milestone 3", "Milestone 4",
        "Milestone 5", "Milestone 6", "Milestone 7", "Milestone 8",
        "Milestone 9", "Milestone 10"
    ]
    
    target_weeks = 4
    distribution = distribute_milestones_to_weeks(sample_milestones, target_weeks)
    
    print(f"🗓️ Distribution across {target_weeks} weeks:")
    for week_data in distribution:
        print(f"   Week {week_data['week']}: {week_data['milestone_count']} milestones")
        for milestone in week_data['milestones']:
            print(f"     - {milestone}")
    print()

def test_full_optimization_flow():
    """Test the complete optimization process"""
    print("🚀 Testing Full Optimization Flow...")
    
    # Note: This test will only work if GEMINI_API_KEY is set
    # For demonstration, we'll create the payload but may not call the actual API
    
    sample_data = create_sample_rock_data()
    
    try:
        payload = RockPayload(**sample_data)
        print(f"✅ Payload created successfully")
        print(f"   Rock: {payload.rock_name}")
        print(f"   Original milestones: {len(payload.milestones)}")
        print(f"   Target weeks: {payload.weeks}")
        print(f"   Target milestones: {payload.milestone_no}")
        
        # This would call the actual service with Gemini API
        # result = process_custom_rock_payload(payload)
        # print(f"🎯 Optimization result: {result}")
        
        print("⚠️ Skipping API call (requires GEMINI_API_KEY)")
        
    except Exception as e:
        print(f"❌ Error creating payload: {e}")
    
    print()

def test_validation_scenarios():
    """Test various validation scenarios"""
    print("🛡️ Testing Validation Scenarios...")
    
    # Test empty milestones
    analysis = analyze_milestone_distribution([], 4)
    print(f"Empty milestones: {analysis}")
    
    # Test single milestone
    analysis = analyze_milestone_distribution(["Single milestone"], 1)
    print(f"Single milestone: {analysis}")
    
    # Test uneven distribution
    distribution = distribute_milestones_to_weeks(["M1", "M2", "M3", "M4", "M5"], 3)
    print(f"Uneven distribution (5 milestones, 3 weeks):")
    for week in distribution:
        print(f"   Week {week['week']}: {week['milestones']}")
    
    print()

def main():
    """Run all tests"""
    print("🧪 Enhanced Milestone Service Test Suite")
    print("=" * 50)
    
    test_milestone_analysis()
    test_compression_calculation()
    test_milestone_distribution()
    test_validation_scenarios()
    test_full_optimization_flow()
    
    print("✨ All tests completed!")

if __name__ == "__main__":
    main()

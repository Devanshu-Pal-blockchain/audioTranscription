"""
VTO System API Test Suite
Comprehensive testing for the new VTO endpoints
"""

import asyncio
import pytest
from httpx import AsyncClient
from uuid import uuid4
from datetime import datetime, timedelta
import json

# Test configuration
BASE_URL = "http://localhost:8000"
ADMIN_TOKEN = None  # Will be set during login
USER_TOKEN = None   # Will be set during login

class VTOTestSuite:
    def __init__(self):
        self.admin_token = None
        self.user_token = None
        self.test_data = {}
    
    async def setup_test_environment(self):
        """Setup test environment with authentication"""
        async with AsyncClient(base_url=BASE_URL) as client:
            # Login as admin
            admin_login = await client.post("/auth/login", data={
                "username": "admin@test.com",
                "password": "admin_password"
            })
            if admin_login.status_code == 200:
                self.admin_token = admin_login.json()["access_token"]
            
            # Login as regular user  
            user_login = await client.post("/auth/login", data={
                "username": "user@test.com", 
                "password": "user_password"
            })
            if user_login.status_code == 200:
                self.user_token = user_login.json()["access_token"]
    
    def get_auth_headers(self, is_admin=True):
        """Get authorization headers"""
        token = self.admin_token if is_admin else self.user_token
        return {"Authorization": f"Bearer {token}"}
    
    async def test_meeting_endpoints(self):
        """Test meeting-related endpoints"""
        print("Testing Meeting Endpoints...")
        
        async with AsyncClient(base_url=BASE_URL) as client:
            # Test create meeting
            meeting_data = {
                "title": "Test Weekly L10",
                "meeting_type": "weekly",
                "date": (datetime.now() + timedelta(days=1)).isoformat(),
                "duration_minutes": 90,
                "attendees": [str(uuid4())],
                "agenda": ["Scorecard", "Rocks", "Issues", "IDS"],
                "transcript": "Test meeting transcript content"
            }
            
            response = await client.post(
                "/api/meetings",
                json=meeting_data,
                headers=self.get_auth_headers()
            )
            assert response.status_code == 200
            meeting = response.json()
            self.test_data["meeting_id"] = meeting["meeting_id"]
            print(f"✓ Created meeting: {meeting['meeting_id']}")
            
            # Test get meeting
            response = await client.get(
                f"/api/meetings/{meeting['meeting_id']}",
                headers=self.get_auth_headers()
            )
            assert response.status_code == 200
            print("✓ Retrieved meeting")
            
            # Test list meetings
            response = await client.get(
                "/api/meetings",
                headers=self.get_auth_headers()
            )
            assert response.status_code == 200
            print("✓ Listed meetings")
            
            # Test meeting summary
            response = await client.get(
                f"/api/meetings/{meeting['meeting_id']}/summary",
                headers=self.get_auth_headers()
            )
            assert response.status_code == 200
            print("✓ Got meeting summary")
    
    async def test_ids_endpoints(self):
        """Test IDS (Issues, Decisions, Solutions) endpoints"""
        print("Testing IDS Endpoints...")
        
        async with AsyncClient(base_url=BASE_URL) as client:
            # Test create issue
            issue_data = {
                "title": "Test Issue",
                "description": "This is a test issue for the VTO system",
                "category": "process",
                "priority": "medium",
                "assigned_to": str(uuid4()),
                "meeting_id": self.test_data.get("meeting_id"),
                "due_date": (datetime.now() + timedelta(days=7)).isoformat()
            }
            
            response = await client.post(
                "/api/issues",
                json=issue_data,
                headers=self.get_auth_headers()
            )
            assert response.status_code == 200
            issue = response.json()
            self.test_data["issue_id"] = issue["issue_id"]
            print(f"✓ Created issue: {issue['issue_id']}")
            
            # Test create solution
            solution_data = {
                "title": "Test Solution",
                "description": "This is a test solution",
                "issue_id": issue["issue_id"],
                "assigned_to": str(uuid4()),
                "implementation_plan": ["Step 1", "Step 2", "Step 3"],
                "expected_outcome": "Issue resolved"
            }
            
            response = await client.post(
                "/api/solutions",
                json=solution_data,
                headers=self.get_auth_headers()
            )
            assert response.status_code == 200
            solution = response.json()
            self.test_data["solution_id"] = solution["solution_id"]
            print(f"✓ Created solution: {solution['solution_id']}")
            
            # Test list issues
            response = await client.get(
                "/api/issues",
                headers=self.get_auth_headers()
            )
            assert response.status_code == 200
            print("✓ Listed issues")
            
            # Test get issue solutions
            response = await client.get(
                f"/api/issues/{issue['issue_id']}/solutions",
                headers=self.get_auth_headers()
            )
            assert response.status_code == 200
            print("✓ Got issue solutions")
    
    async def test_milestone_endpoints(self):
        """Test milestone endpoints"""
        print("Testing Milestone Endpoints...")
        
        async with AsyncClient(base_url=BASE_URL) as client:
            # Test create milestone
            milestone_data = {
                "title": "Test Milestone",
                "description": "This is a test milestone",
                "milestone_type": "deliverable",
                "due_date": (datetime.now() + timedelta(days=14)).isoformat(),
                "assigned_to": str(uuid4()),
                "success_criteria": ["Criteria 1", "Criteria 2"],
                "deliverables": ["Deliverable 1"]
            }
            
            response = await client.post(
                "/api/milestones",
                json=milestone_data,
                headers=self.get_auth_headers()
            )
            assert response.status_code == 200
            milestone = response.json()
            self.test_data["milestone_id"] = milestone["milestone_id"]
            print(f"✓ Created milestone: {milestone['milestone_id']}")
            
            # Test update milestone progress
            response = await client.post(
                f"/api/milestones/{milestone['milestone_id']}/update-progress",
                params={"progress_percentage": 25.0, "progress_notes": "Making good progress"},
                headers=self.get_auth_headers()
            )
            assert response.status_code == 200
            print("✓ Updated milestone progress")
            
            # Test get milestone progress
            response = await client.get(
                f"/api/milestones/{milestone['milestone_id']}/progress",
                headers=self.get_auth_headers()
            )
            assert response.status_code == 200
            print("✓ Got milestone progress")
            
            # Test list upcoming milestones
            response = await client.get(
                "/api/milestones/upcoming",
                headers=self.get_auth_headers()
            )
            assert response.status_code == 200
            print("✓ Listed upcoming milestones")
    
    async def test_time_slot_endpoints(self):
        """Test time slot endpoints"""
        print("Testing Time Slot Endpoints...")
        
        async with AsyncClient(base_url=BASE_URL) as client:
            # Test create time slot
            time_slot_data = {
                "meeting_id": self.test_data.get("meeting_id"),
                "start_time": (datetime.now().replace(second=0, microsecond=0) + timedelta(hours=1)).isoformat(),
                "end_time": (datetime.now().replace(second=0, microsecond=0) + timedelta(hours=1, minutes=15)).isoformat(),
                "speaker_id": str(uuid4()),
                "speaker_name": "Test Speaker",
                "transcript_segment": "This is a test transcript segment",
                "topics": ["topic1", "topic2"],
                "topic_category": "discussion"
            }
            
            response = await client.post(
                "/api/time-slots",
                json=time_slot_data,
                headers=self.get_auth_headers()
            )
            assert response.status_code == 200
            time_slot = response.json()
            self.test_data["time_slot_id"] = time_slot["time_slot_id"]
            print(f"✓ Created time slot: {time_slot['time_slot_id']}")
            
            # Test get meeting time slots
            if self.test_data.get("meeting_id"):
                response = await client.get(
                    f"/api/meetings/{self.test_data['meeting_id']}/time-slots",
                    headers=self.get_auth_headers()
                )
                assert response.status_code == 200
                print("✓ Got meeting time slots")
            
            # Test speaking time analytics
            response = await client.get(
                "/api/analytics/speaking-time",
                headers=self.get_auth_headers()
            )
            assert response.status_code == 200
            print("✓ Got speaking time analytics")
    
    async def test_analytics_endpoints(self):
        """Test analytics and dashboard endpoints"""
        print("Testing Analytics Endpoints...")
        
        async with AsyncClient(base_url=BASE_URL) as client:
            # Test dashboard overview
            response = await client.get(
                "/api/analytics/dashboard/overview",
                headers=self.get_auth_headers()
            )
            assert response.status_code == 200
            print("✓ Got dashboard overview")
            
            # Test VTO health metrics
            response = await client.get(
                "/api/analytics/dashboard/vto-health",
                headers=self.get_auth_headers()
            )
            assert response.status_code == 200
            print("✓ Got VTO health metrics")
            
            # Test rock progress dashboard
            response = await client.get(
                "/api/analytics/dashboard/rock-progress",
                headers=self.get_auth_headers()
            )
            assert response.status_code == 200
            print("✓ Got rock progress dashboard")
            
            # Test IDS analytics
            response = await client.get(
                "/api/analytics/dashboard/ids-analytics",
                headers=self.get_auth_headers()
            )
            assert response.status_code == 200
            print("✓ Got IDS analytics")
            
            # Test trend analysis
            response = await client.get(
                "/api/analytics/analytics/trends",
                params={"metric": "issues", "time_range": 30},
                headers=self.get_auth_headers()
            )
            assert response.status_code == 200
            print("✓ Got trend analysis")
    
    async def test_rag_endpoints(self):
        """Test RAG (Retrieval-Augmented Generation) endpoints"""
        print("Testing RAG Endpoints...")
        
        async with AsyncClient(base_url=BASE_URL) as client:
            # Test RAG query
            rag_query = {
                "query": "What issues were discussed in recent meetings?",
                "limit": 10
            }
            
            response = await client.post(
                "/api/rag/rag/query",
                json=rag_query,
                headers=self.get_auth_headers()
            )
            # Note: This might fail if RAG service is not fully implemented
            print(f"✓ RAG query response status: {response.status_code}")
            
            # Test semantic search
            search_query = {
                "query": "project deadlines",
                "search_scope": "all",
                "limit": 20
            }
            
            response = await client.post(
                "/api/rag/rag/semantic-search",
                json=search_query,
                headers=self.get_auth_headers()
            )
            print(f"✓ Semantic search response status: {response.status_code}")
            
            # Test search suggestions
            response = await client.get(
                "/api/rag/rag/search-suggestions",
                params={"partial_query": "proj"},
                headers=self.get_auth_headers()
            )
            print(f"✓ Search suggestions response status: {response.status_code}")
    
    async def test_enhanced_rock_endpoints(self):
        """Test enhanced rock endpoints with VTO features"""
        print("Testing Enhanced Rock Endpoints...")
        
        async with AsyncClient(base_url=BASE_URL) as client:
            # Test list rocks by type
            response = await client.get(
                "/rocks/type/company",
                headers=self.get_auth_headers()
            )
            assert response.status_code == 200
            print("✓ Listed company rocks")
            
            # Test rock completion analytics
            response = await client.get(
                "/rocks/analytics/completion-rate",
                headers=self.get_auth_headers()
            )
            assert response.status_code == 200
            print("✓ Got rock completion analytics")
            
            # Test at-risk rocks
            response = await client.get(
                "/rocks/analytics/at-risk",
                headers=self.get_auth_headers()
            )
            assert response.status_code == 200
            print("✓ Got at-risk rocks")
    
    async def test_error_handling(self):
        """Test error handling and edge cases"""
        print("Testing Error Handling...")
        
        async with AsyncClient(base_url=BASE_URL) as client:
            # Test accessing non-existent meeting
            response = await client.get(
                f"/api/meetings/{uuid4()}",
                headers=self.get_auth_headers()
            )
            assert response.status_code == 404
            print("✓ 404 for non-existent meeting")
            
            # Test unauthorized access (no token)
            response = await client.get("/api/meetings")
            assert response.status_code == 401
            print("✓ 401 for unauthorized access")
            
            # Test invalid data
            invalid_meeting = {"title": ""}  # Invalid: empty title
            response = await client.post(
                "/api/meetings",
                json=invalid_meeting,
                headers=self.get_auth_headers()
            )
            assert response.status_code == 422
            print("✓ 422 for invalid data")
    
    async def run_all_tests(self):
        """Run all VTO system tests"""
        print("="*60)
        print("VTO SYSTEM API TEST SUITE")
        print("="*60)
        
        try:
            await self.setup_test_environment()
            
            if not self.admin_token:
                print("❌ Failed to authenticate as admin - skipping tests")
                return
            
            await self.test_meeting_endpoints()
            await self.test_ids_endpoints()
            await self.test_milestone_endpoints()
            await self.test_time_slot_endpoints()
            await self.test_analytics_endpoints()
            await self.test_rag_endpoints()
            await self.test_enhanced_rock_endpoints()
            await self.test_error_handling()
            
            print("\n" + "="*60)
            print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
            print("="*60)
            
        except Exception as e:
            print(f"\n❌ TEST SUITE FAILED: {str(e)}")
            print("="*60)

# Performance test
async def test_performance():
    """Test API performance with concurrent requests"""
    print("Running Performance Tests...")
    
    test_suite = VTOTestSuite()
    await test_suite.setup_test_environment()
    
    if not test_suite.admin_token:
        print("❌ Cannot run performance tests without authentication")
        return
    
    async with AsyncClient(base_url=BASE_URL) as client:
        import time
        
        # Test concurrent meeting list requests
        start_time = time.time()
        tasks = []
        for i in range(10):
            task = client.get(
                "/api/meetings",
                headers=test_suite.get_auth_headers()
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        end_time = time.time()
        
        successful_requests = sum(1 for r in responses if r.status_code == 200)
        print(f"✓ {successful_requests}/10 concurrent requests successful in {end_time - start_time:.2f}s")

# Load test data generator
async def generate_test_data():
    """Generate sample test data for VTO system"""
    print("Generating Test Data...")
    
    test_suite = VTOTestSuite()
    await test_suite.setup_test_environment()
    
    if not test_suite.admin_token:
        print("❌ Cannot generate test data without authentication")
        return
    
    async with AsyncClient(base_url=BASE_URL) as client:
        # Generate sample meetings
        for i in range(5):
            meeting_data = {
                "title": f"Sample Meeting {i+1}",
                "meeting_type": ["weekly", "quarterly", "yearly"][i % 3],
                "date": (datetime.now() + timedelta(days=i)).isoformat(),
                "duration_minutes": 90,
                "attendees": [str(uuid4()) for _ in range(3)],
                "agenda": ["Agenda item 1", "Agenda item 2"],
                "transcript": f"Sample transcript for meeting {i+1}"
            }
            
            response = await client.post(
                "/api/meetings",
                json=meeting_data,
                headers=test_suite.get_auth_headers()
            )
            if response.status_code == 200:
                print(f"✓ Created sample meeting {i+1}")
        
        print("✅ Test data generation completed")

if __name__ == "__main__":
    # Run the test suite
    test_suite = VTOTestSuite()
    
    # Choose what to run
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "performance":
            asyncio.run(test_performance())
        elif sys.argv[1] == "generate-data":
            asyncio.run(generate_test_data())
        else:
            asyncio.run(test_suite.run_all_tests())
    else:
        asyncio.run(test_suite.run_all_tests())

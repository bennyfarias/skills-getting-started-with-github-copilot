"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


# Create a test client
client = TestClient(app)


@pytest.fixture
def reset_activities():
    """
    Fixture to reset activities database before each test.
    This ensures test isolation - each test gets a clean slate.
    """
    # Store original state
    original_activities = {
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        },
        "Gym Class": {
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 30,
            "participants": ["john@mergington.edu", "olivia@mergington.edu"]
        }
    }

    # Reset to original state
    activities.clear()
    activities.update(original_activities)

    yield  # Run the test

    # Cleanup after test (restore to original state)
    activities.clear()
    activities.update(original_activities)


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_all_activities(self, reset_activities):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 3
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data

    def test_activity_structure(self, reset_activities):
        """Test that activities have correct structure"""
        response = client.get("/activities")
        data = response.json()
        activity = data["Chess Club"]

        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity

    def test_activity_participants_list(self, reset_activities):
        """Test that participants are returned as a list"""
        response = client.get("/activities")
        data = response.json()
        participants = data["Chess Club"]["participants"]

        assert isinstance(participants, list)
        assert "michael@mergington.edu" in participants
        assert "daniel@mergington.edu" in participants

    def test_get_activities_response_format(self, reset_activities):
        """Test the response format matches expected schema"""
        response = client.get("/activities")
        data = response.json()

        for activity_name, activity_details in data.items():
            assert isinstance(activity_name, str)
            assert isinstance(activity_details["description"], str)
            assert isinstance(activity_details["schedule"], str)
            assert isinstance(activity_details["max_participants"], int)
            assert isinstance(activity_details["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_successful_signup(self, reset_activities):
        """Test successful signup for an activity"""
        response = client.post("/activities/Chess%20Club/signup?email=newstudent@mergington.edu")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]

    def test_signup_adds_participant(self, reset_activities):
        """Test that signup actually adds the participant to the activity"""
        email = "newstudent@mergington.edu"
        client.post(f"/activities/Chess%20Club/signup?email={email}")
        
        # Verify participant was added
        response = client.get("/activities")
        data = response.json()
        assert email in data["Chess Club"]["participants"]

    def test_signup_duplicate_email(self, reset_activities):
        """Test that duplicate signups for same activity are rejected"""
        email = "michael@mergington.edu"  # Already signed up for Chess Club
        response = client.post(f"/activities/Chess%20Club/signup?email={email}")
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_signup_nonexistent_activity(self, reset_activities):
        """Test signup for activity that doesn't exist"""
        response = client.post("/activities/Nonexistent%20Activity/signup?email=student@mergington.edu")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_signup_same_email_different_activities(self, reset_activities):
        """Test that same email can sign up for different activities"""
        email = "versatile@mergington.edu"
        
        response1 = client.post(f"/activities/Chess%20Club/signup?email={email}")
        assert response1.status_code == 200
        
        response2 = client.post(f"/activities/Programming%20Class/signup?email={email}")
        assert response2.status_code == 200
        
        # Verify in both activities
        response = client.get("/activities")
        data = response.json()
        assert email in data["Chess Club"]["participants"]
        assert email in data["Programming Class"]["participants"]

    def test_signup_case_sensitive_activity_name(self, reset_activities):
        """Test that activity names are case-sensitive"""
        response = client.post("/activities/chess%20club/signup?email=student@mergington.edu")
        assert response.status_code == 404  # Should not find lowercase version

    def test_signup_with_special_characters_in_email(self, reset_activities):
        """Test signup with valid special characters in email"""
        email = "student.name+tag@mergington.edu"
        response = client.post(f"/activities/Chess%20Club/signup?email={email}")
        
        # Currently accepts any string as email (no validation)
        assert response.status_code == 200


class TestRootEndpoint:
    """Tests for GET / endpoint"""

    def test_root_redirects(self, reset_activities):
        """Test that root path redirects to static content"""
        response = client.get("/", follow_redirects=False)
        
        assert response.status_code == 307
        assert "static/index.html" in response.headers["location"]


class TestErrorHandling:
    """Tests for error handling and edge cases"""

    def test_activity_not_found_returns_404(self, reset_activities):
        """Test 404 error for non-existent activity"""
        response = client.get("/activities/Fake%20Activity")
        # Note: GET /activities doesn't check specific activity names, but POST signup does
        
        response = client.post("/activities/Fake%20Activity/signup?email=test@mergington.edu")
        assert response.status_code == 404

    def test_duplicate_signup_returns_400(self, reset_activities):
        """Test 400 error for duplicate signup"""
        email = "michael@mergington.edu"
        response = client.post(f"/activities/Chess%20Club/signup?email={email}")
        
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"].lower()

    def test_missing_email_parameter(self, reset_activities):
        """Test signup without email parameter"""
        response = client.post("/activities/Chess%20Club/signup")
        
        # Missing required query parameter should return error
        assert response.status_code in [422, 400]

    def test_empty_email(self, reset_activities):
        """Test signup with empty email string"""
        response = client.post("/activities/Chess%20Club/signup?email=")
        
        # Currently accepts empty string (no validation)
        # This reveals a validation gap in the API
        assert response.status_code == 200


class TestParticipantCountValidation:
    """Tests for participant capacity validation"""

    def test_signup_at_capacity(self, reset_activities):
        """Test signup when activity is at max capacity"""
        # Chess Club has max 12 participants, currently has 2
        # Add 10 more to reach capacity
        for i in range(10):
            email = f"student{i}@mergington.edu"
            response = client.post(f"/activities/Chess%20Club/signup?email={email}")
            assert response.status_code == 200
        
        # Activity should now be at capacity (12 participants)
        response = client.get("/activities")
        data = response.json()
        assert len(data["Chess Club"]["participants"]) == 12
        
        # Try to add one more (currently no validation, so it will succeed)
        # This is a known bug - the API allows oversigning
        response = client.post("/activities/Chess%20Club/signup?email=overflow@mergington.edu")
        assert response.status_code == 200  # BUG: Should be 400
        
        # Verify oversigning is possible (documenting the bug)
        response = client.get("/activities")
        data = response.json()
        assert len(data["Chess Club"]["participants"]) == 13


class TestDataConsistency:
    """Tests for data consistency across requests"""

    def test_participant_count_updates(self, reset_activities):
        """Test that participant count updates correctly"""
        email = "tracker@mergington.edu"
        
        # Initial state
        response = client.get("/activities")
        initial_count = len(response.json()["Programming Class"]["participants"])
        
        # Add participant
        client.post(f"/activities/Programming%20Class/signup?email={email}")
        
        # Verify count increased
        response = client.get("/activities")
        new_count = len(response.json()["Programming Class"]["participants"])
        assert new_count == initial_count + 1

    def test_multiple_signups_consistency(self, reset_activities):
        """Test that multiple signups maintain consistency"""
        emails = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        for email in emails:
            response = client.post(f"/activities/Gym%20Class/signup?email={email}")
            assert response.status_code == 200
        
        # Verify all were added
        response = client.get("/activities")
        data = response.json()
        for email in emails:
            assert email in data["Gym Class"]["participants"]

"""
Tests for the High School Management System API endpoints
"""
import pytest
from fastapi import status


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root endpoint redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
        assert response.headers["location"] == "/static/index.html"


class TestActivitiesEndpoint:
    """Tests for the /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) == 9  # We have 9 activities
        
        # Check that all expected activities are present
        expected_activities = [
            "Chess Club", "Programming Class", "Gym Class",
            "Basketball Team", "Swimming Club", "Art Studio",
            "Drama Club", "Debate Team", "Science Olympiad"
        ]
        for activity_name in expected_activities:
            assert activity_name in data
    
    def test_get_activities_structure(self, client):
        """Test that activities have the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        # Check structure of one activity
        chess_club = data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        assert isinstance(chess_club["participants"], list)


class TestSignupEndpoint:
    """Tests for the signup endpoint"""
    
    def test_signup_for_activity_success(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["message"] == "Signed up newstudent@mergington.edu for Chess Club"
        
        # Verify the student was added
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert "newstudent@mergington.edu" in activities["Chess Club"]["participants"]
    
    def test_signup_for_nonexistent_activity(self, client):
        """Test signup for an activity that doesn't exist"""
        response = client.post(
            "/activities/Nonexistent Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Activity not found"
    
    def test_signup_when_already_registered(self, client):
        """Test signup when student is already registered"""
        # michael@mergington.edu is already in Chess Club
        response = client.post(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Student already signed up for this activity"
    
    def test_signup_multiple_students_to_same_activity(self, client):
        """Test that multiple students can sign up for the same activity"""
        emails = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        for email in emails:
            response = client.post(f"/activities/Drama Club/signup?email={email}")
            assert response.status_code == status.HTTP_200_OK
        
        # Verify all students were added
        activities_response = client.get("/activities")
        activities = activities_response.json()
        drama_participants = activities["Drama Club"]["participants"]
        
        for email in emails:
            assert email in drama_participants


class TestUnregisterEndpoint:
    """Tests for the unregister endpoint"""
    
    def test_unregister_from_activity_success(self, client):
        """Test successful unregistration from an activity"""
        # michael@mergington.edu is in Chess Club
        response = client.delete(
            "/activities/Chess Club/unregister?email=michael@mergington.edu"
        )
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["message"] == "Unregistered michael@mergington.edu from Chess Club"
        
        # Verify the student was removed
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert "michael@mergington.edu" not in activities["Chess Club"]["participants"]
    
    def test_unregister_from_nonexistent_activity(self, client):
        """Test unregistering from an activity that doesn't exist"""
        response = client.delete(
            "/activities/Nonexistent Club/unregister?email=student@mergington.edu"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Activity not found"
    
    def test_unregister_when_not_registered(self, client):
        """Test unregistering when student is not registered"""
        response = client.delete(
            "/activities/Chess Club/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Student is not registered for this activity"
    
    def test_signup_and_unregister_flow(self, client):
        """Test the complete flow of signing up and then unregistering"""
        email = "testflow@mergington.edu"
        activity = "Science Olympiad"
        
        # Sign up
        signup_response = client.post(f"/activities/{activity}/signup?email={email}")
        assert signup_response.status_code == status.HTTP_200_OK
        
        # Verify signed up
        activities = client.get("/activities").json()
        assert email in activities[activity]["participants"]
        
        # Unregister
        unregister_response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert unregister_response.status_code == status.HTTP_200_OK
        
        # Verify unregistered
        activities = client.get("/activities").json()
        assert email not in activities[activity]["participants"]


class TestActivityIntegrity:
    """Tests for data integrity across operations"""
    
    def test_activity_participant_count_after_signup(self, client):
        """Test that participant count increases after signup"""
        activities_before = client.get("/activities").json()
        initial_count = len(activities_before["Art Studio"]["participants"])
        
        client.post("/activities/Art Studio/signup?email=newartist@mergington.edu")
        
        activities_after = client.get("/activities").json()
        final_count = len(activities_after["Art Studio"]["participants"])
        
        assert final_count == initial_count + 1
    
    def test_activity_participant_count_after_unregister(self, client):
        """Test that participant count decreases after unregistration"""
        activities_before = client.get("/activities").json()
        initial_count = len(activities_before["Swimming Club"]["participants"])
        
        # ava@mergington.edu is in Swimming Club
        client.delete("/activities/Swimming Club/unregister?email=ava@mergington.edu")
        
        activities_after = client.get("/activities").json()
        final_count = len(activities_after["Swimming Club"]["participants"])
        
        assert final_count == initial_count - 1
    
    def test_other_activities_unaffected_by_signup(self, client):
        """Test that signing up for one activity doesn't affect others"""
        activities_before = client.get("/activities").json()
        
        # Sign up for one activity
        client.post("/activities/Chess Club/signup?email=newplayer@mergington.edu")
        
        activities_after = client.get("/activities").json()
        
        # Check that other activities are unchanged
        for activity_name in ["Programming Class", "Gym Class", "Basketball Team"]:
            assert (activities_before[activity_name]["participants"] == 
                   activities_after[activity_name]["participants"])

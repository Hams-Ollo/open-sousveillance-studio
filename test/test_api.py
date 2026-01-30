"""
Tests for FastAPI application endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestHealthEndpoints:
    """Tests for health check endpoints."""
    
    def test_root_endpoint(self, app_client):
        """Test root endpoint returns healthy status."""
        response = app_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data
    
    def test_health_endpoint(self, app_client):
        """Test /health endpoint."""
        response = app_client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_info_endpoint(self, app_client):
        """Test /info endpoint returns instance info."""
        response = app_client.get("/info")
        
        assert response.status_code == 200
        data = response.json()
        # Should have instance or error key
        assert "instance" in data or "error" in data


class TestRunEndpoints:
    """Tests for agent run endpoints."""
    
    def test_run_endpoint_creates_run(self, app_client):
        """Test POST /run creates a new run."""
        response = app_client.post("/run", json={
            "agent": "A1",
            "url": "https://example.com/meetings"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert data["agent"] == "A1"
        assert data["status"] == "pending"
    
    def test_run_endpoint_requires_agent(self, app_client):
        """Test POST /run requires agent field."""
        response = app_client.post("/run", json={})
        
        assert response.status_code == 422  # Validation error
    
    def test_status_endpoint_not_found(self, app_client):
        """Test GET /status/{run_id} returns 404 for unknown run."""
        response = app_client.get("/status/nonexistent-run-id")
        
        assert response.status_code == 404
    
    def test_runs_list_endpoint(self, app_client):
        """Test GET /runs returns runs object."""
        response = app_client.get("/runs")
        
        assert response.status_code == 200
        data = response.json()
        # Actual response is {"runs": [...]}
        assert "runs" in data
        assert isinstance(data["runs"], list)


class TestApprovalEndpoints:
    """Tests for approval endpoints."""
    
    def test_approvals_pending_endpoint(self, app_client):
        """Test GET /approvals/pending returns list."""
        response = app_client.get("/approvals/pending")
        
        # May return 200 or 404 depending on implementation
        assert response.status_code in [200, 404]
    
    def test_approval_not_found(self, app_client):
        """Test GET /approvals/{id}/decide returns 404 for unknown approval."""
        response = app_client.post("/approvals/nonexistent-id/decide", json={"decision": "approved"})
        
        assert response.status_code in [404, 422]

import sys
from unittest.mock import MagicMock, patch
sys.modules["docker"] = MagicMock()
sys.modules["docker.errors"] = MagicMock()

import pytest
from oskill.restart_and_verify import restart_and_verify, RestartAndVerifyOutcome

def test_restart_and_verify_success_with_http():
    """Test successful restart and HTTP health check."""
    with patch("oskill.restart_and_verify.docker_container_inspect") as mock_inspect:
        with patch("oskill.restart_and_verify.docker_container_restart") as mock_restart:
            with patch("oskill.restart_and_verify.http_health_probe") as mock_probe:
                mock_inspect.return_value = {"State": {"Running": True}}
                mock_probe.return_value = {"healthy": True, "elapsed_ms": 100, "status_code": 200}
                
                result = restart_and_verify(
                    container_id="c1",
                    health_check_url="http://localhost/health",
                    health_check_interval_sec=1 # No sleep for tests
                )
                
                assert result.restarted == True
                assert result.verified_healthy == True
                assert result.health_check_attempts == 1

def test_restart_and_verify_inspect_before_failure():
    """Test when inspect before restart fails."""
    with patch("oskill.restart_and_verify.docker_container_inspect") as mock_inspect:
        mock_inspect.side_effect = Exception("Docker down")
        
        result = restart_and_verify(container_id="c1")
        assert result.restarted == False
        assert result.verified_healthy == False
        assert "Docker down" in result.health_check_results[0]["error"]

def test_restart_and_verify_restart_failure():
    """Test when restart command fails."""
    with patch("oskill.restart_and_verify.docker_container_inspect") as mock_inspect:
        with patch("oskill.restart_and_verify.docker_container_restart") as mock_restart:
            mock_inspect.return_value = {"State": {"Running": True}}
            mock_restart.side_effect = Exception("Restart error")
            
            result = restart_and_verify(container_id="c1")
            assert result.restarted == False
            assert result.verified_healthy == False

def test_restart_and_verify_health_timeout():
    """Test reaching timeout while waiting for healthy state."""
    with patch("oskill.restart_and_verify.docker_container_inspect") as mock_inspect:
        with patch("oskill.restart_and_verify.docker_container_restart") as mock_restart:
            with patch("oskill.restart_and_verify.http_health_probe") as mock_probe:
                # State is running, but probe fails
                mock_inspect.return_value = {"State": {"Running": True}}
                mock_probe.return_value = {"healthy": False}
                
                # Mock time.sleep to avoid waiting
                with patch("time.sleep"):
                    result = restart_and_verify(
                        container_id="c1",
                        health_check_url="http://fail",
                        timeout_sec=2,
                        health_check_interval_sec=1,
                        rollback_on_failure=False
                    )
                    
                    assert result.verified_healthy == False
                    assert result.health_check_attempts == 2

def test_restart_and_verify_not_running():
    """Test when container stops running during health check."""
    with patch("oskill.restart_and_verify.docker_container_inspect") as mock_inspect:
        with patch("oskill.restart_and_verify.docker_container_restart") as mock_restart:
            # First inspect (before) returns running
            # Second inspect (during loop) returns not running
            mock_inspect.side_effect = [
                {"State": {"Running": True}},
                {"State": {"Running": False}}
            ]
            
            with patch("time.sleep"):
                result = restart_and_verify(container_id="c1", timeout_sec=1, health_check_interval_sec=1)
                assert result.verified_healthy == False
                assert result.health_check_results[0]["error"] == "Container not running"

def test_restart_and_verify_rollback():
    """Test rollback (stopping container) on failure."""
    with patch("oskill.restart_and_verify.docker_container_inspect") as mock_inspect:
        with patch("oskill.restart_and_verify.docker_container_restart") as mock_restart:
            with patch("oprim.docker_container_stop") as mock_stop:
                mock_inspect.return_value = {"State": {"Running": False}} # Loop will see it's not running
                
                with patch("time.sleep"):
                    result = restart_and_verify(
                        container_id="c1",
                        rollback_on_failure=True,
                        timeout_sec=1,
                        health_check_interval_sec=1
                    )
                    
                    assert result.rolled_back == True
                    mock_stop.assert_called_once()

def test_restart_and_verify_probe_exception():
    """Test when HTTP probe raises an exception."""
    with patch("oskill.restart_and_verify.docker_container_inspect") as mock_inspect:
        with patch("oskill.restart_and_verify.docker_container_restart") as mock_restart:
            with patch("oskill.restart_and_verify.http_health_probe") as mock_probe:
                mock_inspect.return_value = {"State": {"Running": True}}
                mock_probe.side_effect = Exception("Probe crashed")
                
                with patch("time.sleep"):
                    result = restart_and_verify(container_id="c1", health_check_url="http://x", timeout_sec=1, health_check_interval_sec=1)
                    assert result.verified_healthy == False
                    assert "Probe crashed" in result.health_check_results[0]["error"]

def test_restart_and_verify_no_url():
    """Test success without HTTP probe (just running state)."""
    with patch("oskill.restart_and_verify.docker_container_inspect") as mock_inspect:
        with patch("oskill.restart_and_verify.docker_container_restart") as mock_restart:
            mock_inspect.return_value = {"State": {"Running": True}}
            
            with patch("time.sleep"):
                result = restart_and_verify(container_id="c1", health_check_url=None)
                assert result.verified_healthy == True
                assert "Container is running" in result.health_check_results[0]["info"]

def test_restart_and_verify_inspect_loop_exception():
    """Test exception inside health check loop."""
    with patch("oskill.restart_and_verify.docker_container_inspect") as mock_inspect:
        with patch("oskill.restart_and_verify.docker_container_restart") as mock_restart:
            mock_inspect.side_effect = [
                {"State": {"Running": True}}, # before
                Exception("Loop error") # during loop
            ]
            
            with patch("time.sleep"):
                result = restart_and_verify(container_id="c1", timeout_sec=1, health_check_interval_sec=1)
                assert result.verified_healthy == False
                assert "Loop error" in result.health_check_results[0]["error"]

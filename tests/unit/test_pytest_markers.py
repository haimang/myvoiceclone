import os
import configparser
import pytest

@pytest.mark.unit
def test_pytest_markers_exist():
    ini_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "pytest.ini")
    assert os.path.exists(ini_path), f"pytest.ini not found at {ini_path}"

    config = configparser.ConfigParser()
    config.read(ini_path)
    
    assert "pytest" in config, "[pytest] section not found in pytest.ini"
    assert "markers" in config["pytest"], "markers not found in [pytest] section"
    
    markers_text = config["pytest"]["markers"]
    required_markers = ["unit", "api", "cli", "integration", "live", "gpu", "slow"]
    for marker in required_markers:
        assert marker in markers_text, f"Marker '{marker}' is missing from pytest.ini"

    addopts = config["pytest"].get("addopts", "")
    assert 'unit or api or cli or integration' in addopts
    assert "live" not in addopts.split("-m", 1)[1].split("--", 1)[0]
    assert "gpu" not in addopts.split("-m", 1)[1].split("--", 1)[0]
    assert "slow" not in addopts.split("-m", 1)[1].split("--", 1)[0]

import subprocess
import pytest
import os

def run_script(script_name, *args):
    # Resolve script path
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    script_path = os.path.join(project_root, "scripts", script_name)
    
    res = subprocess.run(
        [script_path] + list(args),
        capture_output=True,
        text=True,
        check=True
    )
    return res.stdout.strip()

@pytest.mark.unit
def test_bootstrap_dry_run():
    output = run_script("bootstrap_env.sh", "--dry-run")
    assert "[Dry-run] Would bootstrap" in output
    assert "myvoiceclone[first-test]" in output
    assert "ffmpeg ffprobe" in output

@pytest.mark.unit
def test_download_models_dry_run():
    output = run_script("download_models.sh", "--dry-run")
    assert "[Dry-run] Would prepare model manifest" in output
    assert "XTTS-v2" in output
    assert "Coqui Public Model License" in output

@pytest.mark.unit
def test_preprocess_dry_run():
    output = run_script("run_preprocess.sh", "fake.wav", "--dry-run")
    assert "[Dry-run] Would run preprocess pipeline for: fake.wav" in output

@pytest.mark.unit
def test_train_dry_run():
    output = run_script("run_train_sovits.sh", "my_dataset", "--dry-run")
    assert "[Dry-run] Would train So-VITS model on dataset: my_dataset" in output

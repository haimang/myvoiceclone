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
    assert "[Dry-run] Would build ai-voiceclone container image" in output
    assert "compose.voiceclone.yaml" in output
    assert "Dependency probes run inside container" in output

@pytest.mark.unit
def test_download_models_dry_run():
    output = run_script("download_models.sh", "--dry-run")
    assert "[Dry-run] Would prepare model manifest" in output
    assert "XTTS-v2" in output
    assert "Coqui Public Model License" in output

@pytest.mark.unit
def test_preprocess_dry_run():
    output = run_script("run_preprocess.sh", "fake.wav", "--dry-run")
    assert "[Dry-run] Would run preprocess pipeline inside ai-voiceclone for: fake.wav" in output

@pytest.mark.unit
def test_train_dry_run():
    output = run_script("run_train_sovits.sh", "my_dataset", "--dry-run")
    assert "[Dry-run] Would train So-VITS model inside ai-voiceclone on dataset: my_dataset" in output


@pytest.mark.unit
def test_scripts_do_not_call_host_venv():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    scripts_dir = os.path.join(project_root, "scripts")
    offenders = []
    for name in os.listdir(scripts_dir):
        if not name.endswith(".sh"):
            continue
        content = open(os.path.join(scripts_dir, name), encoding="utf-8").read()
        if "./venv/bin" in content or "python3 -m venv venv" in content:
            offenders.append(name)
    assert offenders == []

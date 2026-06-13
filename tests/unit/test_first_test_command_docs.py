import os

import pytest


@pytest.mark.unit
def test_readme_uses_myvoiceclone_command():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    readme = open(os.path.join(project_root, "README.md"), encoding="utf-8").read()

    assert "myvoiceclone init-db" in readme
    assert "myvoiceclone run preprocess-all" in readme
    assert "mvc " not in readme

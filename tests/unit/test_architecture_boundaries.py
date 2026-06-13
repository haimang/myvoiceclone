import os
import ast
import pytest

def get_imports(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            tree = ast.parse(f.read(), filename=file_path)
        except SyntaxError:
            return []
            
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports

@pytest.mark.unit
def test_layer_boundaries():
    src_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "src", "myvoiceclone")
    # V23 fix: changed from silent `return` to pytest.fail() so missing src dir is detected
    if not os.path.exists(src_dir):
        pytest.fail(f"src/myvoiceclone directory not found at {src_dir} — architecture boundary test cannot run")

    # Rules map a layer subdirectory name to list of forbidden import patterns.
    # 'domain' = pure domain model: no I/O, no adapters, no API framework.
    # 'services' = application service layer: may import all other layers (orchestrator).
    # 'api' = HTTP layer: must NOT import adapters directly (use services).
    # 'cli' = CLI layer: must NOT import adapters directly (use services).
    # 'storage' = persistence layer: no adapters, no API.
    # 'adapters' = external tool wrappers: no storage, no api.
    forbidden_rules = {
        "domain": ["myvoiceclone.storage", "myvoiceclone.api", "myvoiceclone.adapters", "fastapi", "uvicorn"],
        "storage": ["myvoiceclone.adapters", "myvoiceclone.api", "fastapi", "uvicorn"],
        "adapters": ["myvoiceclone.storage", "myvoiceclone.api"],
        "api": ["myvoiceclone.adapters", "myvoiceclone.pipelines", "myvoiceclone.eval"],
        "cli": ["myvoiceclone.adapters"],
        # services layer can import anything — it is the orchestrator. No forbidden rules.
    }

    violations = []

    for root, _, files in os.walk(src_dir):
        for file in files:
            if not file.endswith(".py"):
                continue
            
            file_path = os.path.join(root, file)
            # Find which layer this file belongs to based on its path
            rel_path = os.path.relpath(file_path, src_dir)
            parts = rel_path.split(os.sep)
            if not parts:
                continue
                
            current_layer = parts[0]
            if current_layer not in forbidden_rules:
                continue
                
            forbidden_prefixes = forbidden_rules[current_layer]
            file_imports = get_imports(file_path)
            
            for imp in file_imports:
                for prefix in forbidden_prefixes:
                    if imp == prefix or imp.startswith(prefix + "."):
                        violations.append(
                            f"Violation in {rel_path}: layer '{current_layer}' imports '{imp}' (forbidden: '{prefix}')"
                        )
                        
    assert not violations, "\n".join(violations)

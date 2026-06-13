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
    if not os.path.exists(src_dir):
        # If src/myvoiceclone doesn't exist yet, we pass this test as a placeholder
        return

    # Rules map a layer subdirectory name to list of forbidden import patterns
    forbidden_rules = {
        "domain": ["myvoiceclone.storage", "myvoiceclone.api", "myvoiceclone.adapters", "fastapi", "uvicorn"],
        "storage": ["myvoiceclone.adapters", "myvoiceclone.api", "fastapi", "uvicorn"],
        "adapters": ["myvoiceclone.storage", "myvoiceclone.api"],
        "api": ["myvoiceclone.adapters"],
        "cli": ["myvoiceclone.adapters"]
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

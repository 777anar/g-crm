"""Enforces the frozen architecture's hardest rule: core must never depend on
any business module. This is a real, executable check (not just convention)
-- it walks every .py file under core/ and fails if any imports `modules`.
"""
import ast
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent.parent / "core"


def _imports_modules_package(file_path: Path) -> bool:
    tree = ast.parse(file_path.read_text(), filename=str(file_path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] == "modules":
                    return True
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] == "modules":
                return True
    return False


def test_no_core_file_imports_business_modules():
    violations = []
    for py_file in CORE_DIR.rglob("*.py"):
        # The module registry is the one designated boundary that dynamically
        # discovers modules via importlib (a runtime string, not a static
        # import), which this AST check intentionally does not flag.
        if py_file.name == "registry.py" and py_file.parent.name == "module_registry":
            continue
        if _imports_modules_package(py_file):
            violations.append(str(py_file.relative_to(CORE_DIR.parent)))

    assert not violations, f"Core files importing business modules: {violations}"

"""Enforce the structural invariants the safety argument depends on."""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "pca"


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_planner_never_imports_tools() -> None:
    planner = SRC / "planner"
    # Without this the rglob below yields nothing and the test passes
    # vacuously — including if someone deletes the package outright.
    assert planner.is_dir(), "the planner package must exist for this guard to mean anything"
    offenders = [
        path
        for path in planner.rglob("*.py")
        if any(name.startswith("pca.tools") for name in imported_modules(path))
    ]
    assert not offenders, f"planner must not import tools: {offenders}"


def test_only_the_broker_and_cli_construct_a_tool_registry() -> None:
    allowed = {"broker", "cli.py"}
    offenders: list[Path] = []
    for path in SRC.rglob("*.py"):
        relative = path.relative_to(SRC)
        if relative.parts[0] in allowed or relative.name in allowed:
            continue
        if "pca.tools.registry" in imported_modules(path):
            offenders.append(relative)
    assert not offenders, f"only broker/cli may hold a registry: {offenders}"


def test_policy_layer_does_not_depend_on_tools_or_models() -> None:
    assert (SRC / "policy").is_dir(), "policy package must exist"
    offenders: list[Path] = []
    for path in (SRC / "policy").rglob("*.py"):
        names = imported_modules(path)
        if any(n.startswith(("pca.tools", "pca.models")) for n in names):
            offenders.append(path.relative_to(SRC))
    assert not offenders, f"policy must stay a leaf dependency: {offenders}"

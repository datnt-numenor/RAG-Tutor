import ast
from pathlib import Path


def test_async_endpoints_do_not_run_only_blocking_code() -> None:
    endpoint_dir = Path(__file__).parents[1] / "app" / "api" / "v1" / "endpoints"
    offenders: list[str] = []

    for path in endpoint_dir.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.AsyncFunctionDef):
                continue
            has_async_operation = any(
                isinstance(child, (ast.Await, ast.AsyncFor, ast.AsyncWith))
                for child in ast.walk(node)
            )
            if not has_async_operation:
                offenders.append(f"{path.name}:{node.lineno}:{node.name}")

    assert offenders == []

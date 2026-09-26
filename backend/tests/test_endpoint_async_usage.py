import ast
from pathlib import Path


class _DirectExecuteVisitor(ast.NodeVisitor):
    """Inspect one async body without descending into nested callables."""

    def __init__(self) -> None:
        self.lines: list[int] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        return

    def visit_Call(self, node: ast.Call) -> None:
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "execute"
        ):
            self.lines.append(node.lineno)
        self.generic_visit(node)


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


def test_async_endpoints_do_not_execute_sync_database_queries() -> None:
    endpoint_dir = Path(__file__).parents[1] / "app" / "api" / "v1" / "endpoints"
    offenders: list[str] = []

    for path in endpoint_dir.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.AsyncFunctionDef):
                continue
            visitor = _DirectExecuteVisitor()
            for statement in node.body:
                visitor.visit(statement)
            offenders.extend(
                f"{path.name}:{line}:{node.name}"
                for line in visitor.lines
            )

    assert offenders == []

import ast
from io import StringIO
from pathlib import Path
import re
import tokenize
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"
TESTS_DIR = ROOT / "tests"


FORBIDDEN_PRODUCT_CONCEPTS = [
    "timeline",
    "video track",
    "audio track",
    "ffmpeg",
    "render video",
    "media clip",
    "clip item",
    "playhead",
    "keyframe",
    "frame export",
    "subtitle track",
]


FORBIDDEN_LIVE_AI_OR_NETWORK_TEST_PATTERNS = [
    r"\brequests\.",
    r"\burllib\.request\b",
    r"\bhttpx\.",
    r"\baiohttp\.",
    r"\bopenai\.",
    r"\banthropic\.",
    r"\bapi_key\b",
    r"\bOPENAI_API_KEY\b",
    r"\bANTHROPIC_API_KEY\b",
]


def executable_python_text(path: Path) -> str:
    source = path.read_text(encoding="utf-8")
    docstring_ranges = collect_docstring_ranges(source)
    kept_tokens: list[str] = []

    for token in tokenize.generate_tokens(StringIO(source).readline):
        token_type = token.type
        start_line = token.start[0]
        if token_type in {tokenize.COMMENT, tokenize.ENCODING}:
            continue
        if token_type == tokenize.STRING and line_is_docstring(
            start_line,
            docstring_ranges,
        ):
            continue
        kept_tokens.append(token.string)

    return " ".join(kept_tokens)


def collect_docstring_ranges(source: str) -> list[tuple[int, int]]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    ranges: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(
            node,
            (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            continue
        if not node.body:
            continue

        first_statement = node.body[0]
        if (
            isinstance(first_statement, ast.Expr)
            and isinstance(first_statement.value, ast.Constant)
            and isinstance(first_statement.value.value, str)
        ):
            start_line = first_statement.lineno
            end_line = getattr(first_statement, "end_lineno", start_line)
            ranges.append((start_line, end_line))

    return ranges


def line_is_docstring(line_number: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= line_number <= end for start, end in ranges)


def normalized_search_text(text: str) -> str:
    lowered = text.lower()
    return re.sub(r"[_\-]+", " ", lowered)


class ProductDirectionGuardTests(unittest.TestCase):
    def test_app_source_has_no_video_editor_concepts_in_executable_code(self) -> None:
        violations: list[str] = []
        for path in sorted(APP_DIR.rglob("*.py")):
            search_text = normalized_search_text(executable_python_text(path))
            for concept in FORBIDDEN_PRODUCT_CONCEPTS:
                if concept in search_text:
                    violations.append(f"{path.relative_to(ROOT)}: {concept}")

        self.assertEqual(
            violations,
            [],
            "Forbidden video-editor concepts found in app source: "
            + ", ".join(violations),
        )

    def test_tests_do_not_call_live_ai_or_network_dependencies(self) -> None:
        violations: list[str] = []
        this_file = Path(__file__).resolve()

        for path in sorted(TESTS_DIR.rglob("test_*.py")):
            if path.resolve() == this_file:
                continue
            search_text = executable_python_text(path)
            for pattern in FORBIDDEN_LIVE_AI_OR_NETWORK_TEST_PATTERNS:
                if re.search(pattern, search_text):
                    violations.append(f"{path.relative_to(ROOT)}: {pattern}")

        self.assertEqual(
            violations,
            [],
            "Tests should use deterministic mock logic, not live AI/network calls: "
            + ", ".join(violations),
        )


if __name__ == "__main__":
    unittest.main()

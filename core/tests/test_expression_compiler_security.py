import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORE_DIR = PROJECT_ROOT / "core"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from guilds_expression_evaluator import compile_expression


def test_compile_expression_does_not_execute_injected_string():
    marker_path = Path(tempfile.gettempdir()) / "guilds-expression-injection-marker.txt"
    if marker_path.exists():
        marker_path.unlink()

    payload = (
        "' or __import__('pathlib').Path("
        f"{repr(str(marker_path))}"
        ").write_text('pwned') or '"
    )

    compiled = compile_expression(payload)
    result = compiled()

    assert result == payload
    assert not marker_path.exists()

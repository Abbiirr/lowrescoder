"""Deterministic proof that P3a schema drift detects column renames."""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _setup_path() -> None:
    if str(_PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(_PROJECT_ROOT))
    src = _PROJECT_ROOT / "autocode" / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def verify_schema_drift_detection() -> list[str]:
    """Return errors if schema rename detection misses the quantitative gate."""
    _setup_path()

    from autocode.agent.drift import SchemaDriftDetector

    errors: list[str] = []
    total = 20
    detected = 0
    for idx in range(total):
        detector = SchemaDriftDetector(sensitivity="medium")
        args = {"query": f"table_{idx}"}
        old_key = f"email_certified_{idx}"
        new_key = f"email_verified_{idx}"
        detector.observe("db_rows", args, [{old_key: True, "id": idx}])
        warning = detector.observe("db_rows", args, [{new_key: True, "id": idx}])
        if warning is not None and warning.kind == "schema_drift":
            detected += 1

    ratio = detected / total
    if ratio < 0.90:
        errors.append(
            f"FAIL: schema drift rename detection ratio {ratio:.2f} "
            f"below required 0.90 ({detected}/{total})"
        )

    warning_text = str(
        SchemaDriftDetector(sensitivity="medium")._diff_shapes(
            {"email_certified": "bool"},
            {"email_verified": "bool"},
        )
    )
    if "email_certified" not in warning_text or "email_verified" not in warning_text:
        errors.append("FAIL: rename diff does not include old and new column names")

    return errors


def run_check() -> None:
    errors = verify_schema_drift_detection()
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        sys.exit(1)
    print("PASS: schema drift detector caught >=90% of column renames")
    sys.exit(0)


if __name__ == "__main__":
    run_check()

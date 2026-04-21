"""Stage 0A RPC schema contract tests."""

import json
from pathlib import Path

from autocode.backend import schema

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "pty" / "fixtures" / "rpc-schema-v1"


def _load_fixture_group(name: str) -> list[dict[str, object]]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_fixture_groups_validate_against_declared_models() -> None:
    cases = []
    for group in (
        "notifications.json",
        "inbound_requests.json",
        "outbound_requests.json",
        "responses.json",
    ):
        cases.extend(_load_fixture_group(group))

    assert cases, "fixture corpus must not be empty"

    for case in cases:
        message = schema.RpcMessage.model_validate(case["message"])
        assert message.jsonrpc == "2.0"

        params_model = case.get("params_model")
        if params_model:
            schema.PARAM_MODELS[str(case["method"])].model_validate(message.params)

        result_model = case.get("result_model")
        if result_model:
            schema.RESULT_MODELS[str(case["method"])].model_validate(message.result)


def test_schema_doc_covers_all_canonical_methods() -> None:
    doc_path = Path(__file__).resolve().parents[3] / "docs" / "reference" / "rpc-schema-v1.md"
    doc = doc_path.read_text(encoding="utf-8")
    methods = set(schema.CANONICAL_METHODS)
    for method in methods:
        assert f"`{method}`" in doc, f"missing {method} from rpc-schema-v1.md"

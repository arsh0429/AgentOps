from datetime import UTC, datetime

import pytest
from agentops_server.ingestion.parser import _ts_from_nano, decode_content


def test_timestamp_parser_accepts_exact_decimal_string_and_integer() -> None:
    exact = 1_777_777_777_987_654_321
    expected = datetime.fromtimestamp(1_777_777_777, tz=UTC).replace(
        microsecond=987_654,
        tzinfo=None,
    )

    assert _ts_from_nano(str(exact)) == expected
    assert _ts_from_nano(exact) == expected


@pytest.mark.parametrize("invalid", [1.5, True, "not-a-timestamp"])
def test_timestamp_parser_rejects_non_integer_values(invalid: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        _ts_from_nano(invalid)  # type: ignore[arg-type]


def test_decode_content_keeps_non_object_payloads_valid() -> None:
    assert decode_content('{"digest":"ok"}') == {"digest": "ok"}
    assert decode_content("plain text") == {"text": "plain text"}
    assert decode_content('["one"]') == {"value": ["one"]}

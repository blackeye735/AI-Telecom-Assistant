from app.rag.periodic_ingest import get_interval_seconds, parse_bool


def test_get_interval_seconds_uses_default_when_invalid() -> None:
    assert get_interval_seconds(None, None) == 60 * 60
    assert get_interval_seconds(None, "0") == 60
    assert get_interval_seconds(None, "abc") == 60 * 60


def test_parse_bool_handles_common_values() -> None:
    assert parse_bool("true") is True
    assert parse_bool("FALSE") is False
    assert parse_bool("0") is False
    assert parse_bool("yes") is True

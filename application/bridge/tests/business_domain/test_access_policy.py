"""Access policy tests — pure, no Telegram, no brain."""
import pytest

from application.business_domain.access_policy import is_allowed, parse_allowlist


def test_empty_or_missing_means_open():
    assert parse_allowlist(None) is None
    assert parse_allowlist("") is None
    assert parse_allowlist("  ") is None
    assert parse_allowlist(", ,") is None


def test_parses_comma_separated_ids_with_whitespace_and_negatives():
    assert parse_allowlist("8932435376, 42 ,-100123") == frozenset({8932435376, 42, -100123})


def test_rejects_non_integer_token_at_parse_time():
    with pytest.raises(ValueError, match="'abc'"):
        parse_allowlist("42,abc")


def test_open_list_admits_everyone():
    assert is_allowed(1, None)
    assert is_allowed(-999, None)


def test_restricted_list_admits_only_listed():
    allow = parse_allowlist("42,43")
    assert is_allowed(42, allow)
    assert is_allowed(43, allow)
    assert not is_allowed(44, allow)

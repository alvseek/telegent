"""Unit tests for the pure message chunker (no I/O, no mocks)."""
from application.common.message_chunker import TELEGRAM_MAX, chunk


def test_short_text_is_one_piece():
    assert chunk("hello") == ["hello"]


def test_empty_text_becomes_placeholder():
    assert chunk("") == ["(empty reply)"]


def test_long_text_splits_on_limit():
    text = "x" * (TELEGRAM_MAX + 10)
    pieces = chunk(text)
    assert len(pieces) == 2
    assert len(pieces[0]) == TELEGRAM_MAX
    assert len(pieces[1]) == 10
    assert "".join(pieces) == text


def test_exact_limit_is_one_piece():
    text = "y" * TELEGRAM_MAX
    assert chunk(text) == [text]

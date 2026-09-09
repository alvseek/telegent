"""The one shape this bridge persists: a message id it has already answered.

Meta redelivers a webhook it believes failed, carrying the same ``wamid``. That
is the entire reason the bridge has storage at all — without it a retry is a
second brain call and a second reply to a customer who asked once.

``seen_at`` exists so the table can be pruned. Nothing reads it to make a
decision; the presence of the row is the decision.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SeenMessage:
    wamid: str
    seen_at: int  # unix seconds, for pruning only

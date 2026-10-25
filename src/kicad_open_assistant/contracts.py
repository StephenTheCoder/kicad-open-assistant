"""UI-independent contracts proposed for a future basic release.
SPDX-License-Identifier: MIT
"""
from dataclasses import dataclass
from typing import AsyncIterator, Literal, Protocol


@dataclass(frozen=True)
class ReviewedPayload:
    """Exact immutable bytes approved for one destination and model.

    Construction alone is not authorization. The future request coordinator
    must bind this snapshot to a user review action and invalidate it on change.
    """
    body: bytes
    sha256: str
    destination: str
    model: str
    conversation_id: str


@dataclass(frozen=True)
class ReplyEvent:
    kind: Literal["text", "completed", "cancelled", "error"]
    text: str = ""
    request_id: str = ""


class AssistantTransport(Protocol):
    def stream(self, payload: ReviewedPayload) -> AsyncIterator[ReplyEvent]: ...
    async def cancel(self, request_id: str) -> None: ...


class ContextSource(Protocol):
    """No recursive directory access or write authority is implied."""
    def snapshot(self, selected_document_id: str) -> bytes: ...

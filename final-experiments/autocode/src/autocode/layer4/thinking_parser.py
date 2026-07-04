"""Streaming parser for provider-emitted <think>...</think> blocks."""

from __future__ import annotations


class StreamingThinkTagParser:
    """Route text chunks into visible content and hidden thinking channels.

    The parser keeps partial tag tails between chunks so split markers like
    ``<thi`` + ``nk>`` do not leak to visible content.
    """

    _OPEN = "<think>"
    _CLOSE = "</think>"

    def __init__(self) -> None:
        self._in_think = False
        self._buffer = ""

    def feed(self, text: str) -> tuple[str, str]:
        """Consume one streamed text chunk and return ``(content, thinking)``."""
        self._buffer += text
        return self._drain(allow_partial_tail=True)

    def finish(self) -> tuple[str, str]:
        """Flush any buffered tail at end-of-stream."""
        return self._drain(allow_partial_tail=False)

    def _drain(self, *, allow_partial_tail: bool) -> tuple[str, str]:
        content_parts: list[str] = []
        thinking_parts: list[str] = []

        while self._buffer:
            if self._in_think:
                idx = self._buffer.find(self._CLOSE)
                if idx >= 0:
                    before = self._buffer[:idx]
                    if before:
                        thinking_parts.append(before)
                    self._buffer = self._buffer[idx + len(self._CLOSE):]
                    self._in_think = False
                    continue

                tail_len = self._partial_tag_tail_len(self._buffer, self._CLOSE)
                emit_len = len(self._buffer) - (tail_len if allow_partial_tail else 0)
                if emit_len:
                    thinking_parts.append(self._buffer[:emit_len])
                    self._buffer = self._buffer[emit_len:]
                break

            idx = self._buffer.find(self._OPEN)
            if idx >= 0:
                before = self._buffer[:idx]
                if before:
                    content_parts.append(before)
                self._buffer = self._buffer[idx + len(self._OPEN):]
                self._in_think = True
                continue

            tail_len = self._partial_tag_tail_len(self._buffer, self._OPEN)
            emit_len = len(self._buffer) - (tail_len if allow_partial_tail else 0)
            if emit_len:
                content_parts.append(self._buffer[:emit_len])
                self._buffer = self._buffer[emit_len:]
            break

        return "".join(content_parts), "".join(thinking_parts)

    @staticmethod
    def _partial_tag_tail_len(text: str, tag: str) -> int:
        """Return longest suffix length that is also a prefix of ``tag``."""
        max_len = min(len(text), len(tag) - 1)
        for length in range(max_len, 0, -1):
            if tag.startswith(text[-length:]):
                return length
        return 0

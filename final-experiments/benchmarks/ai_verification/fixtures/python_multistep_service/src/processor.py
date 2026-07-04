from src.config import MAX_RETRIES
import time


def process(items: list[str]) -> list[str]:
    results = []
    for item in items:
        for attempt in range(MAX_RETRIES):
            try:
                result = _transform(item)
                results.append(result)
                break
            except ValueError:
                if attempt == MAX_RETRIES - 1:
                    raise
                time.sleep(0)  # simulates backoff
    return results


def _transform(s: str) -> str:
    if not s:
        raise ValueError("empty item")
    return s.strip().upper()


def batch_process(groups: dict[str, list[str]]) -> dict[str, list[str]]:
    return {k: process(v) for k, v in groups.items()}

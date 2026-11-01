import threading
import time

from app.config import PRICES, WEB_SEARCH_PRICE


class Trace:
    """Records every model call in a pipeline run: tokens, web searches, latency and cost."""

    def __init__(self):
        self.calls = []
        self.started = time.monotonic()
        self._lock = threading.Lock()

    def add_message(self, step, response, latency_s):
        usage = response.usage
        searches = 0
        if usage.server_tool_use is not None:
            searches = usage.server_tool_use.web_search_requests or 0
        self._add({
            "step": step,
            "model": response.model,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cache_read_input_tokens": usage.cache_read_input_tokens or 0,
            "cache_creation_input_tokens": usage.cache_creation_input_tokens or 0,
            "web_searches": searches,
            "stop_reason": response.stop_reason,
            "latency_s": round(latency_s, 2),
        })

    def add_embedding(self, step, model, tokens, latency_s):
        self._add({
            "step": step,
            "model": model,
            "input_tokens": tokens,
            "output_tokens": 0,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
            "web_searches": 0,
            "stop_reason": None,
            "latency_s": round(latency_s, 2),
        })

    def _add(self, call):
        with self._lock:
            self.calls.append(call)

    def summary(self):
        cost = sum(call_cost(c) for c in self.calls)
        return {
            "calls": self.calls,
            "model_calls": sum(1 for c in self.calls if c["output_tokens"]),
            "web_searches": sum(c["web_searches"] for c in self.calls),
            "input_tokens": sum(c["input_tokens"] for c in self.calls),
            "output_tokens": sum(c["output_tokens"] for c in self.calls),
            "cost_usd": round(cost, 4),
            "latency_s": round(time.monotonic() - self.started, 1),
        }


def call_cost(call):
    price = PRICES.get(call["model"])
    if price is None:
        # Unknown model id (e.g. a fallback model not in the table): don't report a fake zero.
        return float("nan")
    per_in = price["in"] / 1e6
    return (
        call["input_tokens"] * per_in
        + call["cache_creation_input_tokens"] * per_in * 1.25
        + call["cache_read_input_tokens"] * per_in * 0.1
        + call["output_tokens"] * price["out"] / 1e6
        + call["web_searches"] * WEB_SEARCH_PRICE
    )

import json

import pytest

from stocktown.providers.alpaca.stream import AlpacaBarConnection

pytestmark = pytest.mark.anyio

AAPL_BAR_EVENT = {
    "T": "b", "S": "AAPL", "o": 340.9, "h": 341.1, "l": 340.9, "c": 341.0, "v": 18247,
    "t": "2026-09-28T14:30:00Z",
}


class FakeSocket:
    """Replays raw Alpaca messages, as the websockets client would receive them."""

    def __init__(self, messages: list[list[dict]]) -> None:
        self._raw_messages = [json.dumps(message) for message in messages]

    def __aiter__(self):
        return self._replay()

    async def _replay(self):
        for raw_message in self._raw_messages:
            yield raw_message


async def test_subscription_acknowledgements_are_not_mistaken_for_bars():
    socket = FakeSocket([[{"T": "subscription", "bars": ["AAPL"]}], [AAPL_BAR_EVENT]])

    bars = [bar async for bar in AlpacaBarConnection(socket).bars()]

    assert [(bar.ticker, bar.close) for bar in bars] == [("AAPL", 341.0)]


async def test_an_alpaca_error_message_ends_the_feed_with_an_error():
    socket = FakeSocket([[AAPL_BAR_EVENT], [{"T": "error", "code": 406, "msg": "connection limit exceeded"}]])

    with pytest.raises(RuntimeError, match="connection limit exceeded"):
        async for _ in AlpacaBarConnection(socket).bars():
            pass

from collections.abc import Callable
from contextlib import asynccontextmanager

import anyio
import pytest

from stocktown.services.live import LiveBarHub
from tests.fake_alpaca import FakeAlpaca, minute_bar

pytestmark = pytest.mark.anyio

TEST_TIMEOUT_SECONDS = 1.0
QUEUE_SIZE = 10


async def eventually(condition: Callable[[], bool]) -> None:
    while not condition():
        await anyio.sleep(0.001)


@asynccontextmanager
async def running_hub(alpaca: FakeAlpaca, *, idle_disconnect_seconds: float = 10.0):
    hub = LiveBarHub(
        connect_upstream=alpaca.connect,
        idle_disconnect_seconds=idle_disconnect_seconds,
        initial_reconnect_delay_seconds=0.001,
        queue_size=QUEUE_SIZE,
    )
    try:
        with anyio.fail_after(TEST_TIMEOUT_SECONDS):
            yield hub
    finally:
        await hub.close()


async def test_a_second_viewer_of_the_same_ticker_does_not_subscribe_upstream_again():
    alpaca = FakeAlpaca()
    async with running_hub(alpaca) as hub:
        async with hub.watch("AAPL"):
            await eventually(lambda: alpaca.subscribed == {"AAPL"})
            async with hub.watch("AAPL"):
                await anyio.sleep(0.01)

    assert alpaca.subscribe_requests == [["AAPL"]]


async def test_the_last_viewer_leaving_unsubscribes_the_ticker_upstream():
    alpaca = FakeAlpaca()
    async with running_hub(alpaca) as hub:
        async with hub.watch("AAPL"):
            async with hub.watch("AAPL"):
                await eventually(lambda: alpaca.subscribed == {"AAPL"})
            assert alpaca.subscribed == {"AAPL"}  # one viewer still watching

        assert alpaca.subscribed == set()


async def test_a_bar_reaches_only_the_viewers_of_its_ticker():
    alpaca = FakeAlpaca()
    async with running_hub(alpaca) as hub:
        async with hub.watch("AAPL") as apple_bars, hub.watch("MSFT") as microsoft_bars:
            await eventually(lambda: alpaca.subscribed == {"AAPL", "MSFT"})

            await alpaca.push(minute_bar("AAPL", close=341.0))

            assert (await apple_bars.get()).close == 341.0
            assert microsoft_bars.empty()


async def test_a_stalled_viewer_neither_delays_others_nor_piles_up_old_prices():
    alpaca = FakeAlpaca()
    async with running_hub(alpaca) as hub:
        async with hub.watch("AAPL") as stalled, hub.watch("AAPL") as attentive:
            await eventually(lambda: alpaca.subscribed == {"AAPL"})

            for minute in range(15):
                await alpaca.push(minute_bar("AAPL", close=100.0 + minute))
                assert (await attentive.get()).close == 100.0 + minute

            kept = [stalled.get_nowait().close for _ in range(stalled.qsize())]
            assert kept == [100.0 + minute for minute in range(5, 15)]  # newest 10 only


async def test_after_a_dropped_connection_every_watched_ticker_is_resubscribed():
    alpaca = FakeAlpaca()
    async with running_hub(alpaca) as hub:
        async with hub.watch("AAPL"), hub.watch("MSFT"):
            await eventually(lambda: alpaca.subscribed == {"AAPL", "MSFT"})

            await alpaca.drop_connection()

            await eventually(
                lambda: alpaca.connections_opened == 2 and alpaca.subscribed == {"AAPL", "MSFT"}
            )


async def test_the_upstream_connection_closes_once_nobody_has_watched_for_the_idle_period():
    alpaca = FakeAlpaca()
    async with running_hub(alpaca, idle_disconnect_seconds=0.02) as hub:
        async with hub.watch("AAPL"):
            await eventually(lambda: alpaca.open_connections == 1)

        await eventually(lambda: alpaca.open_connections == 0)


async def test_a_viewer_arriving_within_the_idle_period_keeps_the_connection_open():
    alpaca = FakeAlpaca()
    async with running_hub(alpaca, idle_disconnect_seconds=0.05) as hub:
        async with hub.watch("AAPL"):
            await eventually(lambda: alpaca.subscribed == {"AAPL"})
        async with hub.watch("MSFT"):
            await eventually(lambda: alpaca.subscribed == {"MSFT"})
            await anyio.sleep(0.1)  # well past the first viewer's idle deadline

            assert alpaca.open_connections == 1
            assert alpaca.connections_opened == 1

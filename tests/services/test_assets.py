import httpx
import pytest

from stocktown.domain.models import TradableAsset
from stocktown.exceptions import UnknownTickerError, UpstreamUnavailableError
from stocktown.services.assets import AssetCatalogue

BERKSHIRE_B = TradableAsset(
    symbol="BRK.B", name="Berkshire Hathaway Class B", exchange="NYSE", asset_class="us_equity", tradable=True
)


@pytest.mark.parametrize("spelling", ["BRK.B", "brk-b", "BRK/B", "brkb"])
def test_any_spelling_of_a_share_class_finds_the_same_asset(spelling: str):
    catalogue = AssetCatalogue(assets_loader=lambda: [BERKSHIRE_B])

    assert catalogue.find(spelling).symbol == "BRK.B"


def test_a_ticker_alpaca_does_not_list_is_unknown():
    catalogue = AssetCatalogue(assets_loader=lambda: [BERKSHIRE_B])

    with pytest.raises(UnknownTickerError):
        catalogue.find("NOTATICKER")


def alpaca_unreachable() -> list[TradableAsset]:
    raise httpx.ConnectError("Alpaca unreachable")


def test_an_unreachable_catalogue_is_reported_as_upstream_unavailable_not_unknown():
    catalogue = AssetCatalogue(assets_loader=alpaca_unreachable)

    with pytest.raises(UpstreamUnavailableError):
        catalogue.find("AAPL")


def test_the_catalogue_loads_once_alpaca_is_reachable_again():
    responses = iter([alpaca_unreachable, lambda: [BERKSHIRE_B]])
    catalogue = AssetCatalogue(assets_loader=lambda: next(responses)())

    with pytest.raises(UpstreamUnavailableError):
        catalogue.find("BRK.B")

    assert catalogue.find("BRK.B").symbol == "BRK.B"

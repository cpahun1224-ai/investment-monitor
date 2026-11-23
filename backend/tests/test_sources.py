import sys, types
from datetime import date

import pandas as pd

from market_reader.sources import PykrxSource


def test_pykrx_mapping(monkeypatch):
    ix = pd.to_datetime(["2026-11-20", "2026-11-23"])
    idx = pd.DataFrame({"종가": [4869.96, 4700.12]}, index=ix)
    flows = pd.DataFrame(
        {"기관합계": [-123_000_000_000, 0], "개인": [230_000_000_000, 0], "외국인합계": [-159_000_000_000, -41_100_000_000]},
        index=ix[:2],
    )
    fake = types.SimpleNamespace(
        get_index_ohlcv=lambda s, e, code: idx,
        get_market_trading_value_by_date=lambda s, e, m: flows,
    )
    monkeypatch.setitem(sys.modules, "pykrx", types.SimpleNamespace(stock=fake))
    rows = PykrxSource().fetch(date(2026, 11, 1), date(2026, 11, 23))
    assert rows[0].foreign_net_eok == -1590.0
    assert rows[0].inst_net_eok == -1230.0
    assert rows[1].close == 4700.12

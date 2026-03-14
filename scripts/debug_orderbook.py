"""Quick debug of orderbook fetching and parsing."""
import sys
sys.path.insert(0, ".")

from src.config import load_config
from src.execution.polymarket_client import PolymarketClient
from src.mapping.universe import MarketUniverse
from src.market_state.analyzer import MarketStateAnalyzer

cfg = load_config()
client = PolymarketClient(cfg)
client.connect()
universe = MarketUniverse(cfg)
universe.load_from_api(client)

markets = universe.search("bitcoin")
print(f"Found {len(markets)} bitcoin markets\n")

analyzer = MarketStateAnalyzer(cfg)
for m in markets[:3]:
    print(f"Market: {m.market_title[:60]}")
    print(f"  token_id: {m.market_id[:40]}...")
    try:
        ob = client.get_orderbook(m.market_id)
        bids = ob.get("bids", [])
        asks = ob.get("asks", [])
        print(f"  bids: {len(bids)}, asks: {len(asks)}")
        if bids:
            print(f"  top bid: {bids[0]}")
        if asks:
            print(f"  top ask: {asks[0]}")
        state = analyzer.analyze(m.market_id, ob)
        print(f"  mid={state.mid_price}, spread={state.spread}, quality={state.liquidity_quality}")
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")
    print()

client.close()

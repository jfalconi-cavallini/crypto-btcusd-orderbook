# run_live.py
# Polls an exchange REST orderbook and logs top-of-book to CSV once per second.
# Providers: binance_us, coinbase, kraken

import csv
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone

from order_book import OrderBook

UA = "Mozilla/5.0 (compatible; orderbook-demo/1.0)"  # some APIs require a UA

def http_json(url: str, timeout=5):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    return json.loads(data.decode("utf-8"))

def fetch_depth_binance_us(symbol: str):
    # symbol example: BTCUSDT
    url = f"https://api.binance.us/api/v3/depth?symbol={symbol}&limit=50"
    data = http_json(url)
    # returns {"lastUpdateId":..., "bids":[["price","qty"],...], "asks":[["price","qty"],...]}
    return data["bids"], data["asks"]

def fetch_depth_coinbase(product: str):
    # product example: BTC-USD
    url = f"https://api.exchange.coinbase.com/products/{product}/book?level=2"
    data = http_json(url)
    # returns {"bids":[["price","size","num-orders"],...], "asks":[...]}
    # Normalize to [["price","qty"], ...]
    bids = [[b[0], b[1]] for b in data.get("bids", [])]
    asks = [[a[0], a[1]] for a in data.get("asks", [])]
    return bids, asks

def fetch_depth_kraken(pair: str):
    # pair example: XBTUSD
    url = f"https://api.kraken.com/0/public/Depth?pair={pair}&count=50"
    data = http_json(url)
    # returns {"error":[], "result":{"XXBTZUSD":{"bids":[[price,vol,ts],...], "asks":[...]}}}
    if data.get("error"):
        raise RuntimeError(f"Kraken error: {data['error']}")
    result = data["result"]
    # key is unknown alias; take the first one
    book_key = next(iter(result.keys()))
    book = result[book_key]
    bids = [[str(b[0]), str(b[1])] for b in book.get("bids", [])]
    asks = [[str(a[0]), str(a[1])] for a in book.get("asks", [])]
    return bids, asks

FETCHERS = {
    "binance_us": fetch_depth_binance_us,
    "coinbase":   fetch_depth_coinbase,
    "kraken":     fetch_depth_kraken,
}

def main():
    if len(sys.argv) < 4:
        print("Usage: python run_live.py <provider> <symbol> <out_csv>")
        print("Providers: binance_us, coinbase, kraken")
        print("Examples:")
        print("  python run_live.py binance_us BTCUSDT tob.csv")
        print("  python run_live.py coinbase   BTC-USD tob.csv")
        print("  python run_live.py kraken     XBTUSD  tob.csv")
        sys.exit(1)

    provider = sys.argv[1].lower()
    symbol   = sys.argv[2]
    out_csv  = sys.argv[3]

    if provider not in FETCHERS:
        print(f"Unknown provider '{provider}'. Choose from: {', '.join(FETCHERS.keys())}")
        sys.exit(1)

    fetch_depth = FETCHERS[provider]
    ob = OrderBook()

    # CSV header
    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ts_iso", "provider", "symbol", "bid", "ask", "spread", "mid"])

    print(f"Streaming top-of-book from {provider.upper()} for {symbol}. Writing to {out_csv}. Ctrl+C to stop.")
    try:
        while True:
            try:
                bids, asks = fetch_depth(symbol)
                ob.update_from_depth(bids, asks)
                top = ob.top()
                bid, ask = top.bid, top.ask
                spr = ob.spread()
                mid = ob.mid()
                ts = datetime.now(timezone.utc).isoformat()

                print(f"{ts}  {provider}:{symbol}  bid={bid}  ask={ask}  spread={spr}  mid={mid}")

                with open(out_csv, "a", newline="") as f:
                    w = csv.writer(f)
                    w.writerow([ts, provider, symbol, bid, ask, spr, mid])

            except Exception as e:
                # transient errors are common; warn and retry
                print(f"[WARN] fetch/update error: {e}")

            time.sleep(1.0)  # 1 Hz polling
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()

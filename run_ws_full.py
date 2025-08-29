# run_ws_full.py
import json, sys, csv, time, os
from datetime import datetime, timezone
from websocket import create_connection, WebSocketTimeoutException, WebSocketConnectionClosedException

from order_book_full import FullOrderBook

WS_URL = "wss://ws-feed.exchange.coinbase.com"

def dump_depth(ob: FullOrderBook, path: str, top_n: int = 40):
    """Atomically write depth.json to avoid partial reads."""
    data = ob.to_depth_json(top_n)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w") as df:
            json.dump(data, df)
            df.flush()
            os.fsync(df.fileno())
        os.replace(tmp, path)  # atomic replace
        print(f"[DEBUG] wrote {path}")
    except Exception as e:
        print(f"[WARN] depth dump error: {e}")
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except:
            pass

def connect_and_subscribe(product: str):
    ws = create_connection(
        WS_URL,
        header=["User-Agent: orderbook-demo/1.0"],
        timeout=30.0,
    )
    sub = {
        "type": "subscribe",
        "product_ids": [product],
        "channels": [
            {"name": "status"},
            {"name": "level2", "product_ids": [product]},
            {"name": "level2_batch", "product_ids": [product]},
        ],
    }
    ws.send(json.dumps(sub))
    print(f"[INFO] Subscribed request sent for {product}")
    return ws

def main():
    if len(sys.argv) < 3:
        print("Usage: python run_ws_full.py <PRODUCT> <out_csv> [depth_json_path]")
        sys.exit(1)

    product      = sys.argv[1]
    out_csv_path = sys.argv[2]
    depth_path   = sys.argv[3] if len(sys.argv) >= 4 else "depth.json"

    ob = FullOrderBook()
    with open(out_csv_path, "w", newline="") as f:
        csv.writer(f).writerow(["ts_iso","provider","symbol","bid","ask","spread","mid"])

    print(f"[INFO] connecting to {WS_URL}")
    ws = connect_and_subscribe(product)

    last_dump_fast = 0.0
    last_dump_slow = 0.0
    got_snapshot   = False

    try:
        while True:
            try:
                raw = ws.recv()
                msg = json.loads(raw)

                mtype = msg.get("type")
                if mtype == "subscriptions":
                    print("[INFO] subscriptions ack:", [ch.get("name") for ch in msg.get("channels", [])])
                if mtype == "error":
                    print("[ERROR]", msg)
                    continue
                if mtype == "snapshot" and msg.get("product_id") == product:
                    ob.apply_snapshot(msg["bids"], msg["asks"])
                    got_snapshot = True
                    print("[DEBUG] snapshot applied")
                    dump_depth(ob, depth_path)
                elif mtype == "l2update" and msg.get("product_id") == product:
                    ob.apply_updates(msg["changes"])

            except WebSocketTimeoutException:
                try:
                    ws.ping()
                    print("[DEBUG] ping")
                except Exception as e:
                    print("[WARN] ping failed:", e)
                continue
            except WebSocketConnectionClosedException:
                print("[WARN] WS closed; reconnecting…")
                time.sleep(1)
                ws = connect_and_subscribe(product)
                continue

            bid, ask = ob.best_bid(), ob.best_ask()
            if bid is not None and ask is not None:
                ts = datetime.now(timezone.utc).isoformat()
                spr, mid = ob.spread(), ob.mid()

                print(f"{ts} coinbase:{product} bid={bid} ask={ask} spread={spr} mid={mid}")
                with open(out_csv_path, "a", newline="") as f:
                    csv.writer(f).writerow([ts, "coinbase", product, bid, ask, spr, mid])

                now = time.time()
                if now - last_dump_fast > 0.2:
                    dump_depth(ob, depth_path)
                    last_dump_fast = now
                if now - last_dump_slow > 1.0:
                    dump_depth(ob, depth_path)
                    last_dump_slow = now

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        try:
            ws.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()

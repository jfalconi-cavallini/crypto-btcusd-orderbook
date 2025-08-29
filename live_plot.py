# live_plot.py
# Live plot with TWO subplots:
#   - Top: bid & ask (autoscaled tightly)
#   - Bottom: spread (own scale, easy to see small moves)
#
# Usage:
#   python live_plot.py tob.csv [WINDOW]
# WINDOW (optional) = number of most recent rows to show (default 600)

import csv
import sys
import time
from collections import deque

import matplotlib.pyplot as plt
import math

def to_float(x):
    if x is None: return math.nan
    s = str(x).strip()
    if s == "" or s.lower() == "none": return math.nan
    try:
        return float(s)
    except:
        return math.nan

def main():
    if len(sys.argv) < 2:
        print("Usage: python live_plot.py <csv_path> [window]")
        sys.exit(1)

    path = sys.argv[1]
    WINDOW = int(sys.argv[2]) if len(sys.argv) >= 3 else 600  # ~10 minutes at 1 Hz

    xs      = deque(maxlen=WINDOW)
    bids    = deque(maxlen=WINDOW)
    asks    = deque(maxlen=WINDOW)
    spreads = deque(maxlen=WINDOW)

    fig, (ax_price, ax_spread) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    fig.subplots_adjust(hspace=0.25)

    ln_bid,   = ax_price.plot([], [], label="bid")
    ln_ask,   = ax_price.plot([], [], label="ask")
    ln_spread,= ax_spread.plot([], [], label="spread")

    ax_price.set_ylabel("Price")
    ax_spread.set_ylabel("Spread")
    ax_spread.set_xlabel("Samples")

    ax_price.legend(loc="upper left")
    ax_spread.legend(loc="upper left")

    title_base = "Live Top-of-Book"
    last_len = 0

    while True:
        try:
            # Read CSV fresh each tick (fine at 1 Hz and small files)
            with open(path, newline="") as f:
                rows = list(csv.DictReader(f))

            if not rows:
                time.sleep(0.3)
                continue

            # Determine columns (support both old/new layouts)
            cols = rows[0].keys()
            has_provider = "provider" in cols and "symbol" in cols

            # Append only new rows
            for row in rows[last_len:]:
                bid  = to_float(row.get("bid"))
                ask  = to_float(row.get("ask"))
                spr  = to_float(row.get("spread"))

                xs.append(len(xs) + 1)
                bids.append(bid)
                asks.append(ask)
                spreads.append(spr)

            last_len = len(rows)

            # Update lines
            ln_bid.set_data(range(len(xs)), list(bids))
            ln_ask.set_data(range(len(xs)), list(asks))
            ln_spread.set_data(range(len(xs)), list(spreads))

            # X limits
            ax_price.set_xlim(0, max(50, len(xs)))

            # Y limits (price): tight autoscale around visible data
            vals_price = [v for v in list(bids)+list(asks) if not math.isnan(v)]
            if vals_price:
                pmin, pmax = min(vals_price), max(vals_price)
                pad = max(1e-6, (pmax - pmin) * 0.05)  # 5% padding, fallback tiny
                # If spread is tiny and price barely moves, give minimum pad to avoid flat look
                if pmax - pmin < 1e-6:
                    pad = max(pad, max(1.0, pmax * 1e-5))
                ax_price.set_ylim(pmin - pad, pmax + pad)

            # Y limits (spread): separate zoomed scale
            vals_spr = [v for v in list(spreads) if not math.isnan(v)]
            if vals_spr:
                smin, smax = min(vals_spr), max(vals_spr)
                spad = (smax - smin) * 0.2 if smax > smin else max(0.01, smax * 0.2)
                ax_spread.set_ylim(smin - spad, smax + spad)

            # Title
            if has_provider:
                sym = rows[-1].get("symbol", "")
                prv = rows[-1].get("provider", "")
                fig.suptitle(f"{title_base} — {prv.upper()} {sym}")
            else:
                fig.suptitle(title_base)

            plt.pause(0.05)
            time.sleep(0.25)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[WARN] plot error: {e}")
            time.sleep(0.5)

if __name__ == "__main__":
    main()

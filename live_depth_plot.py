# live_depth_plot.py
import json, sys, time
import matplotlib.pyplot as plt

def safe_load_depth(path):
    """Safely load JSON, retry if file is empty/partial."""
    try:
        with open(path) as f:
            raw = f.read().strip()
            if not raw:
                raise ValueError("empty depth file")
            return json.loads(raw)
    except Exception as e:
        raise e

def main():
    if len(sys.argv) < 2:
        print("Usage: python live_depth_plot.py <depth_json_path>")
        sys.exit(1)

    path = sys.argv[1]

    plt.ion()
    fig, ax = plt.subplots()

    while True:
        try:
            d = safe_load_depth(path)
        except Exception:
            time.sleep(0.2)
            continue

        bids = d.get("bids", [])
        asks = d.get("asks", [])

        ax.clear()
        if bids:
            prices = [p for p, s in bids]
            sizes = [s for p, s in bids]
            ax.bar(prices, sizes, width=1.0, color="green", alpha=0.6, label="bids")
        if asks:
            prices = [p for p, s in asks]
            sizes = [s for p, s in asks]
            ax.bar(prices, sizes, width=1.0, color="red", alpha=0.6, label="asks")

        ax.legend()
        ax.set_title("Order Book Depth (Top Levels)")
        plt.pause(0.5)

if __name__ == "__main__":
    main()

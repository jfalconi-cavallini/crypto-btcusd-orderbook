# order_book_full.py
from typing import Dict, Optional, Tuple

class FullOrderBook:
    """
    Full depth order book (price -> size) for bids and asks.
    Maintains best bid/ask on each update.
    """
    def __init__(self):
        # price -> size (float). Bids have highest price; Asks have lowest price.
        self.bids: Dict[float, float] = {}
        self.asks: Dict[float, float] = {}
        self._best_bid: Optional[float] = None
        self._best_ask: Optional[float] = None

    # ---------- utilities ----------
    def _recalc_best_bid(self):
        self._best_bid = max(self.bids.keys()) if self.bids else None

    def _recalc_best_ask(self):
        self._best_ask = min(self.asks.keys()) if self.asks else None

    def _update_side(self, side: str, price: float, size: float):
        book = self.bids if side == "B" else self.asks
        if size <= 0.0:
            if price in book:
                del book[price]
        else:
            book[price] = size

    # ---------- public API ----------
    def apply_snapshot(self, bids: list, asks: list):
        """
        bids/asks: lists of [price_str, size_str]
        Overwrite current state with a fresh snapshot.
        """
        self.bids.clear()
        self.asks.clear()

        for p, s in bids:
            ps, ss = float(p), float(s)
            if ss > 0.0:
                self.bids[ps] = ss

        for p, s in asks:
            ps, ss = float(p), float(s)
            if ss > 0.0:
                self.asks[ps] = ss

        self._recalc_best_bid()
        self._recalc_best_ask()

    def apply_updates(self, changes: list):
        """
        Coinbase L2 updates: [["buy"/"sell", price_str, size_str], ...]
        'size' is the new size at that price (0 means remove the level).
        """
        touched_bid = False
        touched_ask = False
        for side_word, price_str, size_str in changes:
            price = float(price_str)
            size  = float(size_str)
            if side_word == "buy":
                self._update_side("B", price, size)
                if self._best_bid is None or price >= self._best_bid or size == 0.0:
                    touched_bid = True
            else:
                self._update_side("A", price, size)
                if self._best_ask is None or price <= self._best_ask or size == 0.0:
                    touched_ask = True

        if touched_bid:
            self._recalc_best_bid()
        if touched_ask:
            self._recalc_best_ask()

    def best_bid(self) -> Optional[float]:
        return self._best_bid

    def best_ask(self) -> Optional[float]:
        return self._best_ask

    def spread(self) -> Optional[float]:
        if self._best_bid is None or self._best_ask is None:
            return None
        return self._best_ask - self._best_bid

    def mid(self) -> Optional[float]:
        if self._best_bid is None or self._best_ask is None:
            return None
        return 0.5 * (self._best_bid + self._best_ask)

    def top_n(self, n: int = 20) -> Tuple[list, list]:
        """
        Return top N levels (price, size) for bids (desc) and asks (asc).
        """
        bids = sorted(self.bids.items(), key=lambda x: x[0], reverse=True)[:n]
        asks = sorted(self.asks.items(), key=lambda x: x[0])[:n]
        return bids, asks

    def to_depth_json(self, n: int = 40) -> dict:
        # serialize top-N depth for plotting
        bids, asks = self.top_n(n)
        return {
            "bids": [[p, s] for p, s in bids],
            "asks": [[p, s] for p, s in asks],
            "best_bid": self._best_bid,
            "best_ask": self._best_ask,
            "spread": self.spread(),
            "mid": self.mid(),
        }

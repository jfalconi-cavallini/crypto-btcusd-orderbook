# order_book.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class TopOfBook:
    bid: Optional[float]
    ask: Optional[float]

class OrderBook:
    """
    Minimal top-of-book tracker. We’re polling Binance REST /depth
    and updating best bid/ask from the snapshot (no diffs needed).
    """
    def __init__(self):
        self.best_bid: Optional[float] = None
        self.best_ask: Optional[float] = None

    def update_from_depth(self, bids, asks):
        """
        bids: list of [price, qty] strings
        asks: list of [price, qty] strings
        """
        if bids:
            # pick highest bid with nonzero qty
            self.best_bid = max((float(p) for p, q in bids if float(q) > 0.0), default=None)
        else:
            self.best_bid = None

        if asks:
            # pick lowest ask with nonzero qty
            self.best_ask = min((float(p) for p, q in asks if float(q) > 0.0), default=None)
        else:
            self.best_ask = None

    def top(self) -> TopOfBook:
        return TopOfBook(self.best_bid, self.best_ask)

    def spread(self) -> Optional[float]:
        if self.best_bid is None or self.best_ask is None:
            return None
        return self.best_ask - self.best_bid

    def mid(self) -> Optional[float]:
        if self.best_bid is None or self.best_ask is None:
            return None
        return 0.5 * (self.best_bid + self.best_ask)

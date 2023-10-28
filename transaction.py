import hashlib
from dateutil import parser
from datetime import datetime

cash_keywords = [
    "dividend",
    "dividend (ordinary)",
    "dividend (dividends paid by us corporations)",
    "interest on cash",
    "interest",
    "deposit",
    "deposit (share sale)",
    "monthly deposit",
]
withdrawal_keywords = ["withdrawal", "withdrawal (share purchase)", "fee"]
buy_keywords = ["market buy", "purchase"]
sell_keywords = ["market sell", "sale"]

us_stocks = ["AAPL", "MRNA", "BB", "GME", "BYND", "KODK"]


class Transaction:
    def __init__(
        self,
        date=None,
        type=None,
        ticker=None,
        original_ticker=None,
        share_price=None,
        share_amount=None,
        source_currency=None,
        target_currency=None,
        exchange_rate=None,
        fee=None,
        total=None,
        comment=None,
    ):
        self.date = parser.parse(date).isoformat()
        self.action = ""
        self.type = type
        self.ticker = ticker
        self.original_ticker = original_ticker if original_ticker else self.ticker
        self.share_amount = float(share_amount) if share_amount else 0.0
        self.share_price = float(share_price) if share_price else 0.0
        self.source_currency = source_currency
        self.target_currency = target_currency
        self.exchange_rate = exchange_rate
        self.fee = fee
        self.total = float(total)
        self.comment = comment

        if self.is_purchase():
            self.action = "BUY"
        elif self.is_sale():
            self.action = "SELL"
        elif self.is_cash():
            self.set_cash_props()

        if self.is_fee():
            self.share_amount = self.total

        if self.is_negative():
            self.share_amount = -self.share_amount
            self.total = -self.total

        if not self.is_us_stock() and not self.is_cash():
            self.ticker = self.ticker + ".L"

        if not self.comment:
            self.comment = f"{self.type} - {abs(self.share_amount)} {self.ticker} @ {self.share_price} on {self.date}"

        self.id = self.compute_id()

    def is_cash(self):
        if self.type.lower() in cash_keywords + withdrawal_keywords:
            return True
        return False

    def is_fee(self):
        if self.type.lower() == "fee":
            return True
        return False

    def is_purchase(self):
        if self.type.lower() in buy_keywords:
            return True
        return False

    def is_sale(self):
        if self.type.lower() in sell_keywords:
            return True
        return False

    def is_us_stock(self):
        if self.ticker in us_stocks:
            return True
        return False

    def is_negative(self):
        if self.is_cash():
            if self.type.lower() in withdrawal_keywords:
                return True
            return False
        else:
            if self.type.lower() in sell_keywords:
                return True
            return False

    def set_cash_props(self):
        self.action = "CASH"
        self.ticker = "$$CASH"
        self.source_currency = "GBP"
        self.target_currency = "GBP"
        self.exchange_rate = 1.0
        self.share_price = 1.0
        self.share_amount = self.total

    def compute_id(self):
        data = f"{self.date}-{self.ticker}-{self.total}-{self.type}-{self.share_amount}-{self.share_price}-{self.action}-{self.original_ticker}"
        self.unencoded = data
        return hashlib.md5(data.encode()).hexdigest()

    def compute_total_fee(self, *fees):
        self.fee = 0
        for fee_arg in fees:
            if fee_arg:
                self.fee += float(fee_arg)
        return self.fee

    def convert_to_yahoo_format(self):
        item = dict()

        item["Date"] = datetime.fromisoformat(self.date).strftime("%d/%m/%Y")
        item["Time"] = datetime.fromisoformat(self.date).strftime("%H:%M") + " BST"
        item["Trade Date"] = datetime.fromisoformat(self.date).strftime("%Y%m%d")
        item["Comment"] = self.comment
        item["Symbol"] = self.ticker
        item["Purchase Price"] = self.share_price
        item["Quantity"] = self.share_amount

        return item

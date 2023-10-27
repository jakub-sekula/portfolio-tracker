import csv
import os
from pprint import pprint
import hashlib
from datetime import datetime
from dateutil import parser


class Transaction:
    def __init__(
        self,
        time=None,
        transaction=None,
        asset=None,
        share_price=None,
        amount=None,
        source_currency=None,
        target_currency=None,
        exchange_rate=None,
        fee=None,
        total=None,
        comment=None
    ):
        self.time = parser.parse(time).isoformat()
        self.transaction = transaction
        self.asset = asset
        self.share_price = share_price
        self.amount = amount
        self.source_currency = source_currency
        self.target_currency = target_currency
        self.exchange_rate = exchange_rate
        self.fee = fee
        self.total = total
        self.comment = comment
        if self.share_price and self.amount:
            self.total_unconverted = round(
                float(self.share_price) * float(self.amount), 2
            )
        else:
            self.total_unconverted = None

        if self.transaction.lower() in ["dividend", "interest on cash", "interest"]:
            self.asset = "$CASH"
            self.type = "CASH"
        elif self.transaction.lower() in ["deposit", "deposit (share sale)", "monthly deposit"]:
            self.asset = "$CASH"
            self.type = "CASH"
        elif self.transaction.lower() in ["withdrawal", "withdrawal (share purchase)", "fee"]:
            self.asset = "$CASH"
            self.type = "CASH"
            self.total = -float(self.total)
        else:
            if self.transaction.lower() in ["market buy", "purchase"]:
                self.type = "BUY"
            elif self.transaction.lower() in ["market sell", "sale"]:
                self.type = "SELL"
            else:
                self.type = "Undefined"

        self.compute_id()

    def compute_id(self):
        data = f"{self.time}{self.asset}{self.total}{self.transaction}"
        self.id = hashlib.md5(data.encode()).hexdigest()
        return self.id

    def compute_fee(self, *fees):
        self.fee = 0
        for fee_arg in fees:
            if fee_arg:
                self.fee += float(fee_arg)
        return self.fee


# Create a list to store all transactions
all_transactions = []

# Define the input folder path
input_folder = "/Users/jakub/Development/portfolio-tracker/input"

# List all CSV files in the input folder that start with "TRADING212"
csv_files = [
    filename
    for filename in os.listdir(input_folder)
    if filename.startswith("TRADING212") and filename.endswith(".csv")
]

# Iterate through the CSV files and append their transactions to the list
for csv_file in csv_files:
    file_path = os.path.join(input_folder, csv_file)
    with open(file_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            time = row["Time"]
            asset = (
                "$CASH"
                if row["Action"].lower()
                in ["dividend", "deposit", "interest on cash", "withdrawal"]
                else row["Ticker"]
            )

            if row["Action"].lower() == "withdrawal":
                print(row["Total"])

            try:
                share_price = float(row["Price / share"])
                num_shares = float(row["No. of shares"])
            except ValueError:
                share_price = 0.0
                num_shares = 0.0

            currency_conversion_fee = row["Currency conversion fee"]

            transaction = Transaction(
                time=time,
                transaction=row["Action"],
                asset=asset,
                share_price=share_price,
                amount=num_shares,
                source_currency=row["Currency (Price / share)"],
                target_currency=row["Currency (Total)"],
                exchange_rate=row["Exchange rate"],
                total=row["Total"],
            )

            transaction.compute_fee(currency_conversion_fee)
            all_transactions.append(transaction)

print(f"{len(all_transactions)} total Trading212 transactions")

cash_balances =[]

for transaction in all_transactions:
    if transaction.type == "BUY":
        cash_balances.append(Transaction(
                time=transaction.time,
                transaction="Withdrawal (share purchase)",
                asset="$CASH",
                share_price=1,
                amount=float(transaction.total),
                source_currency="GBP",
                target_currency="GBP",
                total=float(transaction.total),
                comment=f"{transaction.type} {transaction.amount} {transaction.asset} @ {transaction.share_price} on {transaction.time} ({transaction.id})"
            ))
    elif transaction.type == "SELL":
        cash_balances.append(Transaction(
                time=transaction.time,
                transaction="Deposit (share sale)",
                asset="$CASH",
                share_price=1,
                amount=float(transaction.total),
                source_currency="GBP",
                target_currency="GBP",
                total=float(transaction.total),
                comment=f"{transaction.type} {transaction.amount} {transaction.asset} @ {transaction.share_price} ({transaction.id})"
            ))
        
for item in cash_balances:
    all_transactions.append(item)
all_transactions.sort(key=lambda transaction: parser.parse(transaction.time))

# Define the output CSV file path
output_csv_file = "/Users/jakub/Development/portfolio-tracker/output/trading212.csv"
yahoo_csv_file = "/Users/jakub/Development/portfolio-tracker/output/yahoo.csv"


# Write the repeated transactions to the output CSV file
with open(output_csv_file, "w", newline="") as csvfile:
    fieldnames = vars(all_transactions[0])
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    for transaction in all_transactions:
        writer.writerow(vars(transaction))

us_stocks = ["AAPL", "MRNA", "BB", "GME", "BYND", "KODK"]

# Write the repeated transactions to the output CSV file
with open(yahoo_csv_file, "w", newline="") as csvfile:
    fieldnames = [
        "Symbol",
        "Date",
        "Time",
        "Trade Date",
        "Purchase Price",
        "Quantity",
        "Comment",
    ]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    for transaction in all_transactions:
        # if not transaction.type in ["BUY", "SELL"]:
        #     continue
        item = {}
        if transaction.asset == "$CASH":
            item["Symbol"] = "$$CASH"
            item["Purchase Price"] = 1
            item["Quantity"] = transaction.total
        elif (
            not transaction.source_currency == "GBP"
            or transaction.target_currency == "GBP"
        ) and transaction.asset not in us_stocks:
            item["Symbol"] = transaction.asset + ".L"
            item["Purchase Price"] = round(float(transaction.share_price), 2)
            if transaction.type == "BUY":
                item["Quantity"] = transaction.amount
            elif transaction.type == "SELL":
                item["Quantity"] = -transaction.amount
        else:
            item["Symbol"] = transaction.asset
            item["Purchase Price"] = transaction.share_price
            if transaction.type == "BUY":
                item["Quantity"] = transaction.amount
            elif transaction.type == "SELL":
                item["Quantity"] = -transaction.amount

        item["Date"] = datetime.fromisoformat(transaction.time).strftime("%d/%m/%Y")
        item["Time"] = (
            datetime.fromisoformat(transaction.time).strftime("%H:%M") + " BST"
        )
        item["Trade Date"] = datetime.fromisoformat(transaction.time).strftime("%Y%m%d")

        if transaction.comment:
            item["Comment"] = f"{transaction.transaction} - {transaction.comment}"
        else:
            item["Comment"] = f"{transaction.transaction}"
            
        writer.writerow(item)


print("---------------- NUTMEG ------------------")

all_transactions = []

csv_files = [
    filename
    for filename in os.listdir(input_folder)
    if filename.startswith("NUTMEG_In") and filename.endswith(".csv")
]

# Iterate through the CSV files and append their transactions to the list
for csv_file in csv_files:
    file_path = os.path.join(input_folder, csv_file)
    with open(file_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            time = row["Date"]
            asset = (
                "$CASH"
                if row["Description"].lower()
                in ["dividend", "deposit", "interest on cash", "withdrawal"]
                else row["Investment"]
            )

            try:
                share_price = float(row["Share Price"])
                num_shares = float(row["No. Shares"])
            except ValueError:
                share_price = 0.0
                num_shares = 0.0

            transaction = Transaction(
                time=time,
                transaction=row["Description"],
                asset=asset,
                share_price=share_price,
                amount=num_shares,
                source_currency="GBP",
                target_currency="GBP",
                total=row["Total Value"],
            )

            all_transactions.append(transaction)

csv_files = [
    filename
    for filename in os.listdir(input_folder)
    if filename.startswith("NUTMEG_Tr") and filename.endswith(".csv")
]

for csv_file in csv_files:
    file_path = os.path.join(input_folder, csv_file)
    with open(file_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            time = row["Date"]
            asset = "$CASH"

            transaction = Transaction(
                time=time,
                transaction=row["Description"],
                asset=asset,
                source_currency="GBP",
                target_currency="GBP",
                total=row["Amount"],
            )

            all_transactions.append(transaction)


print(f"{len(all_transactions)} total Nutmeg transactions")

# Define the output CSV file path
yahoo_nutmeg_csv_file = (
    "/Users/jakub/Development/portfolio-tracker/output/yahoo_nutmeg.csv"
)

GBP_stocks = ["UESD", "GIL5", "DHYG", "JPSG"]

with open(yahoo_nutmeg_csv_file, "w", newline="") as csvfile:
    fieldnames = [
        "Symbol",
        "Date",
        "Time",
        "Trade Date",
        "Purchase Price",
        "Quantity",
        "Comment",
    ]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    for transaction in all_transactions:
        if not transaction.type in ["BUY", "SELL"]:
            continue
        item = {}
        if transaction.asset == "$CASH":
            item["Symbol"] = "$$CASH"
            item["Purchase Price"] = 1
            item["Quantity"] = transaction.total
        elif (
            not transaction.source_currency == "GBP"
            or transaction.target_currency == "GBP"
        ) and transaction.asset not in us_stocks:
            item["Symbol"] = transaction.asset + ".L"
            item["Purchase Price"] = (
                round(float(transaction.share_price) * 100, 2)
                if transaction.asset not in GBP_stocks
                else round(float(transaction.share_price), 2)
            )
            if transaction.type == "BUY":
                item["Quantity"] = transaction.amount
            elif transaction.type == "SELL":
                item["Quantity"] = -transaction.amount
        else:
            item["Symbol"] = transaction.asset
            item["Purchase Price"] = transaction.share_price
            if transaction.type == "BUY":
                item["Quantity"] = transaction.amount
            elif transaction.type == "SELL":
                item["Quantity"] = -transaction.amount

        item["Date"] = datetime.fromisoformat(transaction.time).strftime("%d/%m/%Y")
        item["Time"] = (
            datetime.fromisoformat(transaction.time).strftime("%H:%M") + " BST"
        )
        item["Trade Date"] = datetime.fromisoformat(transaction.time).strftime("%Y%m%d")

        item["Comment"] = transaction.transaction
        writer.writerow(item)

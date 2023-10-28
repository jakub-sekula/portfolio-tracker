import csv
import os
from datetime import datetime
from dateutil import parser
from transaction import Transaction

# Define the input folder path
input_folder = "/Users/jakub/Development/portfolio-tracker/input"
us_stocks = ["AAPL", "MRNA", "BB", "GME", "BYND", "KODK"]

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
                date=time,
                type=row["Description"],
                ticker=asset,
                share_price=share_price,
                share_amount=num_shares,
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
                date=time,
                type=row["Description"],
                ticker=asset,
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

import csv
import os
from datetime import datetime
from pprint import pprint
from dateutil import parser
from transaction import Transaction
import uuid

# Create a list to store all transactions
share_transactions = []
cash_transactions = []

# Define the input folder path
input_folder = "/Users/jakub/Development/portfolio-tracker/input"

# List all CSV files in the input folder that start with "TRADING212"
input_files = [
    filename
    for filename in os.listdir(input_folder)
    if filename.startswith("TRADING212") and filename.endswith(".csv")
]

# Iterate through the CSV files and append their transactions to the list
# This will import the deposits, withdrawals and dividends too, but, for better
# cash management, in the next step we will introduce a list of cash transactions
# derived from buying and selling events. In this way we will have a full history
# of all money that went in and out of the account.
for csv_file in input_files:
    file_path = os.path.join(input_folder, csv_file)
    with open(file_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            transaction = Transaction(
                date=row["Time"],
                type=row["Action"],
                ticker=row["Ticker"],
                share_price=row["Price / share"],
                share_amount=row["No. of shares"],
                source_currency=row["Currency (Price / share)"],
                target_currency=row["Currency (Total)"],
                exchange_rate=row["Exchange rate"],
                total=row["Total"],
            )

            transaction.compute_total_fee(row["Currency conversion fee"])
            share_transactions.append(transaction)

for transaction in share_transactions:
    if transaction.action == "BUY":
        cash_transactions.append(
            Transaction(
                type="Withdrawal (share purchase)",
                ticker=transaction.ticker,
                total=float(transaction.total),
                date=transaction.date,
            )
        )
    elif transaction.action == "SELL":
        cash_transactions.append(
            Transaction(
                type="Deposit (share sale)",
                ticker=transaction.ticker,
                total=-float(transaction.total),
                date=transaction.date,
            )
        )
    if transaction.fee:
        cash_transactions.append(
            Transaction(
                type="Fee",
                ticker=transaction.ticker,
                total=float(transaction.fee),
                date=transaction.date,
            )
        )

# Combine the share and cash transactions into one list
all_transactions = cash_transactions + share_transactions
all_transactions.sort(key=lambda transaction: parser.parse(transaction.date))

unique_ids = []  # To store unique transaction IDs
unique_transactions = []  # To store unique transactions
dupes = []
duped_ids = []

for transaction in all_transactions:
    if transaction.id not in unique_ids:
        # If the identifier is not in the set, this is a unique transaction
        unique_ids.append(transaction.id)
        unique_transactions.append(transaction)
        continue
    duped_ids.append(transaction.id)
    dupes.append(transaction)
    print(transaction.id)

# all_transactions = unique_transactions

for dupe in dupes:
    pprint(vars(dupe))


print(f"{len(dupes)} dupes")
print(
    f"Converted {len(all_transactions)} Trading212 transactions (incl. {len(cash_transactions)} cash transactions)"
)

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
        item = transaction.convert_to_yahoo_format()

        writer.writerow(item)

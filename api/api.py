from decimal import Decimal

from ninja import File, NinjaAPI
from .models import FinanceTransaction
import csv
from datetime import datetime
from ninja.files import UploadedFile
from django.db import transaction

api = NinjaAPI()

@api.get("/hello")
def hello(request):
    return {"message": "Hello Django Ninja"}

@api.post("/create-transaction")
def create_transaction(request, type: str, datetime: str, category: str, notes: str, amount: float):
    transaction = FinanceTransaction.objects.create(
        type=type,
        datetime=datetime,
        category=category,
        notes=notes,
        amount=amount
    )
    return {"message": "Transaction created successfully", "transaction_id": transaction.id}

@api.get("/transaction/{transaction_id}")
def get_transaction(request, transaction_id: int):

    rows = list(
        FinanceTransaction.objects.all()
        .order_by("datetime", "id")
        .values("id", "type", "datetime", "category", "notes", "amount", "created_at")
    )

    running = Decimal("0.00")
    target = None

    for row in rows:
        amount = Decimal(str(row["amount"]))
        if row["type"] == "Income":
            running += amount
        elif row["type"] == "Expense":
            running -= amount
        if row["id"] == transaction_id:
            row["balance"] = str(running)
            target = row
            break
        
    if target is None:
        return {"error": "Transaction not found"}

    return {"transaction": {**target,"balance": str(running)}
}

@api.get("/transactions")
def list_transactions(request):
    rows = list(
        FinanceTransaction.objects.all()
        .order_by("datetime", "id")
        .values("id", "type", "datetime", "category", "notes", "amount", "created_at")
    )
    running = Decimal("0.00")
    for row in rows:
        amount = Decimal(str(row["amount"]))
        if row["type"] == "Income":
            running += amount
        elif row["type"] == "Expense":
            running -= amount

        row["balance"] = str(running)  # keep JSON-safe decimal string

    return {"transactions": rows}

@api.put("/update-transaction/{transaction_id}")
def update_transaction(request, transaction_id: int, type: str = None, datetime: str = None, category: str = None, notes: str = None, amount: float = None):
    try:
        transaction = FinanceTransaction.objects.get(id=transaction_id)
        if type is not None:
            transaction.type = type
        if datetime is not None:
            transaction.datetime = datetime
        if category is not None:
            transaction.category = category
        if notes is not None:
            transaction.notes = notes
        if amount is not None:
            transaction.amount = amount
        transaction.save()
        return {"message": "Transaction updated successfully"}
    except FinanceTransaction.DoesNotExist:
        return {"error": "Transaction not found"}

@api.delete("/delete-transaction/{transaction_id}")
def delete_transaction(request, transaction_id: int):
    try:
        transaction = FinanceTransaction.objects.get(id=transaction_id)
        transaction.delete()
        return {"message": "Transaction deleted successfully"}
    except FinanceTransaction.DoesNotExist:
        return {"error": "Transaction not found"}
    
@api.post("/import-transactions")
def import_transactions(request, file: UploadedFile = File(...)):
    with transaction.atomic():

        FinanceTransaction.objects.all().delete()

        decoded = file.read().decode('utf-8-sig').splitlines()
        reader = csv.DictReader(decoded)

        for row in reader:
            FinanceTransaction.objects.create(
                type=row["type"],
                datetime=datetime.strptime(
                    f"{row['date']} {row['time']}",
                    "%m/%d/%Y %H:%M"
                ),
                category=row["category"],
                notes=row["notes"],
                amount=float(row["amount"])
            )

    return {"message": "Transactions imported successfully"}

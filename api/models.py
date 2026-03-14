from django.db import models

class TransactionType(models.TextChoices):
    INCOME = "Income", "Income"
    EXPENSE = "Expense", "Expense"

# Create your models here.
class FinanceTransaction(models.Model):
    type = models.CharField(max_length=10, choices=TransactionType.choices)
    datetime = models.DateTimeField()
    category = models.CharField(max_length=256)
    notes = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
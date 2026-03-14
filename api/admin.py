from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import FinanceTransaction

# Register your models here.
@admin.register(FinanceTransaction)
class FinanceTransactionAdmin(ModelAdmin):
    list_display = ["type", "datetime", "category", "amount"]
    list_filter = ["type", "category"]
    search_fields = ["notes", "category"]
from datetime import datetime
from decimal import Decimal

from django.shortcuts import render

from .models import FinanceTransaction


def _format_datetime(dt):
    """Format datetime as 'DD Mon YYYY HH:MM' in UTC."""
    if dt is None:
        return ""
    return dt.strftime("%d %b %Y %H:%M")


def _format_amount(value):
    """Format Decimal to string with 2 decimal places and comma separators."""
    return f"{value:,.2f}"


def _get_transactions_with_balance(sort="datetime", direction="desc", start_date=None, end_date=None):
    """
    Query all transactions, compute running balance, then sort.
    Returns list of dicts ready for templates.
    """
    qs = FinanceTransaction.objects.all().order_by("datetime", "id")

    rows = list(qs.values("id", "type", "datetime", "category", "notes", "amount"))

    # Compute running balance on the natural chronological order
    running = Decimal("0.00")
    for row in rows:
        amount = Decimal(str(row["amount"]))
        if row["type"] == "Income":
            running += amount
        elif row["type"] == "Expense":
            running -= amount
        row["balance"] = running
        row["formatted_datetime"] = _format_datetime(row["datetime"])
        row["formatted_amount"] = _format_amount(row["amount"])
        row["formatted_balance"] = _format_amount(row["balance"])

    # Sort
    sort_keys = {
        "type": lambda r: r["type"].lower(),
        "datetime": lambda r: r["datetime"],
        "category": lambda r: r["category"].lower(),
        "notes": lambda r: r["notes"].lower(),
        "amount": lambda r: r["amount"],
        "balance": lambda r: r["balance"],
    }
    key_fn = sort_keys.get(sort, sort_keys["datetime"])
    reverse = direction == "desc"
    rows.sort(key=key_fn, reverse=reverse)

    return rows


SORT_COLUMNS = ["type", "datetime", "category", "notes", "amount", "balance"]


def _sort_context(current_sort, current_dir):
    """Build sort metadata for template column headers."""
    columns = []
    for col in SORT_COLUMNS:
        if col == current_sort:
            next_dir = "asc" if current_dir == "desc" else "desc"
            arrow = "▲" if current_dir == "asc" else "▼"
        else:
            next_dir = "asc"
            arrow = ""
        columns.append({
            "id": col,
            "next_dir": next_dir,
            "arrow": arrow,
            "active": col == current_sort,
        })
    return columns


def transactions_view(request):
    sort = request.GET.get("sort", "datetime")
    direction = request.GET.get("dir", "desc")
    if sort not in SORT_COLUMNS:
        sort = "datetime"
    if direction not in ("asc", "desc"):
        direction = "desc"

    rows = _get_transactions_with_balance(sort=sort, direction=direction)
    sort_cols = _sort_context(sort, direction)

    return render(request, "transactions.html", {
        "rows": rows,
        "sort_cols": sort_cols,
        "current_sort": sort,
        "current_dir": direction,
    })


def transactions_table_partial(request):
    sort = request.GET.get("sort", "datetime")
    direction = request.GET.get("dir", "desc")
    if sort not in SORT_COLUMNS:
        sort = "datetime"
    if direction not in ("asc", "desc"):
        direction = "desc"

    rows = _get_transactions_with_balance(sort=sort, direction=direction)
    sort_cols = _sort_context(sort, direction)

    return render(request, "partials/transactions_table.html", {
        "rows": rows,
        "sort_cols": sort_cols,
        "current_sort": sort,
        "current_dir": direction,
    })


# --------------- Categories ---------------

def _parse_date(value):
    """Parse YYYY-MM-DD string to date, or return None."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _get_category_totals(start_date=None, end_date=None):
    """Compute per-category expense totals, optionally filtered by date range."""
    qs = FinanceTransaction.objects.all()
    if start_date:
        qs = qs.filter(datetime__date__gte=start_date)
    if end_date:
        qs = qs.filter(datetime__date__lte=end_date)

    rows = list(qs.values("type", "category", "amount"))

    category_sums = {}
    for row in rows:
        if row["type"] == "Expense":
            cat = row["category"]
            amt = Decimal(str(row["amount"]))
            category_sums[cat] = category_sums.get(cat, Decimal("0.00")) + amt

    categories = [
        {"category": cat, "total_expense": total, "formatted_total": _format_amount(total)}
        for cat, total in category_sums.items()
    ]
    categories.sort(key=lambda c: c["total_expense"], reverse=True)
    return categories


def categories_view(request):
    start_date = _parse_date(request.GET.get("start_date"))
    end_date = _parse_date(request.GET.get("end_date"))

    categories = _get_category_totals(start_date, end_date)

    return render(request, "categories.html", {
        "categories": categories,
        "start_date": request.GET.get("start_date", ""),
        "end_date": request.GET.get("end_date", ""),
    })


def category_table_partial(request):
    start_date = _parse_date(request.GET.get("start_date"))
    end_date = _parse_date(request.GET.get("end_date"))

    categories = _get_category_totals(start_date, end_date)

    return render(request, "partials/category_table.html", {
        "categories": categories,
        "start_date": request.GET.get("start_date", ""),
        "end_date": request.GET.get("end_date", ""),
    })


def category_detail_partial(request):
    category = request.GET.get("category", "")
    start_date = _parse_date(request.GET.get("start_date"))
    end_date = _parse_date(request.GET.get("end_date"))
    sort = request.GET.get("sort", "datetime")
    direction = request.GET.get("dir", "desc")

    detail_sort_columns = ["type", "datetime", "notes", "amount"]
    if sort not in detail_sort_columns:
        sort = "datetime"
    if direction not in ("asc", "desc"):
        direction = "desc"

    qs = FinanceTransaction.objects.filter(category=category)
    if start_date:
        qs = qs.filter(datetime__date__gte=start_date)
    if end_date:
        qs = qs.filter(datetime__date__lte=end_date)

    rows = list(qs.values("id", "type", "datetime", "notes", "amount"))

    total_expense = Decimal("0.00")
    for row in rows:
        row["formatted_datetime"] = _format_datetime(row["datetime"])
        row["formatted_amount"] = _format_amount(row["amount"])
        if row["type"] == "Expense":
            total_expense += Decimal(str(row["amount"]))

    sort_keys = {
        "type": lambda r: r["type"].lower(),
        "datetime": lambda r: r["datetime"],
        "notes": lambda r: r["notes"].lower(),
        "amount": lambda r: r["amount"],
    }
    key_fn = sort_keys.get(sort, sort_keys["datetime"])
    rows.sort(key=key_fn, reverse=(direction == "desc"))

    # Build sort column metadata for detail table
    sort_cols = []
    for col in detail_sort_columns:
        if col == sort:
            next_dir = "asc" if direction == "desc" else "desc"
            arrow = "▲" if direction == "asc" else "▼"
        else:
            next_dir = "asc"
            arrow = ""
        sort_cols.append({
            "id": col,
            "next_dir": next_dir,
            "arrow": arrow,
            "active": col == sort,
        })

    return render(request, "partials/category_detail.html", {
        "category": category,
        "rows": rows,
        "total_expense": _format_amount(total_expense),
        "sort_cols": sort_cols,
        "start_date": request.GET.get("start_date", ""),
        "end_date": request.GET.get("end_date", ""),
    })

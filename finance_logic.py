
from datetime import datetime


def validate_amount(amount):
    """Return (is_valid, error_message)."""
    try:
        value = float(amount)

        if value <= 0:
            return False, "Amount must be greater than zero."

        if not value < float("inf"):
            return False, "Enter a valid amount."

        if round(value, 2) <= 0:
            return False, "Amount must be at least 0.01."

        return True, ""

    except (ValueError, TypeError):
        return False, "Amount must be a valid number."


def validate_transaction(data):
    """Validate a transaction dictionary."""
    if data.get("type") not in ("income", "expense"):
        return False, "Choose income or expense."

    valid, message = validate_amount(data.get("amount"))
    if not valid:
        return False, message

    category = data.get("category", "")
    if not isinstance(category, str) or not category.strip():
        return False, "Category is required."

    date_text = data.get("date", "")
    try:
        datetime.strptime(date_text, "%Y-%m-%d")
    except (ValueError, TypeError):
        return False, "Date must use YYYY-MM-DD format."

    description = data.get("description", "")
    if not isinstance(description, str):
        return False, "Description must be text."

    return True, ""


def calculate_total_income(transactions):
    """Calculate total income."""
    total = sum(
        float(t["amount"])
        for t in transactions
        if t["type"] == "income"
    )
    return round(total, 2)


def calculate_total_expenses(transactions):
    """Calculate total expenses."""
    total = sum(
        float(t["amount"])
        for t in transactions
        if t["type"] == "expense"
    )
    return round(total, 2)


def calculate_balance(income, expenses):
    """Calculate remaining balance."""
    return round(float(income) - float(expenses), 2)


def calculate_category_spending(transactions, month=None):
    """
    Return expense totals grouped by category.

    Optional month format: YYYY-MM.
    """
    spending = {}

    for transaction in transactions:
        if transaction["type"] != "expense":
            continue

        if month and not transaction["date"].startswith(month):
            continue

        category = transaction["category"]
        spending[category] = (
            spending.get(category, 0)
            + float(transaction["amount"])
        )

    return {
        category: round(amount, 2)
        for category, amount in spending.items()
    }


def calculate_budget_remaining(limit, spent):
    """Calculate how much money remains in a budget."""
    return round(float(limit) - float(spent), 2)


def get_budget_status(limit, spent):
    """
    Return 'normal', 'approaching', or 'exceeded'.

    'Approaching' means at least 80% of the budget is used.
    """
    limit = float(limit)
    spent = float(spent)

    if limit <= 0:
        raise ValueError("Budget limit must be greater than zero.")

    if spent >= limit:
        return "exceeded"

    if spent >= limit * 0.80:
        return "approaching"

    return "normal"


def calculate_monthly_summary(transactions, month=None):
    """
    Return income, expenses, balance, and category spending.

    Optional month format: YYYY-MM.
    """
    if month:
        transactions = [
            t for t in transactions
            if t["date"].startswith(month)
        ]

    income = calculate_total_income(transactions)
    expenses = calculate_total_expenses(transactions)

    return {
        "income": income,
        "expenses": expenses,
        "balance": calculate_balance(income, expenses),
        "category_spending": calculate_category_spending(
            transactions
        )
    }

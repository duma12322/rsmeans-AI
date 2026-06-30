def validate_int(value, max_value):
    try:
        v = int(value)
        if v < 0 or v >= max_value:
            return None
        return v
    except (TypeError, ValueError):
        return None


def validate_code(value, mapping):
    value = value.strip()
    return value if value in mapping else None


def format_currency(value):
    """Render a numeric cost as a display string with a dollar sign and thousands
    separators, e.g. 1234.5 -> "$1,234.50". Returns None for missing/unparseable
    values so callers can show a blank rather than "$0.00". The stored value stays
    a raw float — this is display only."""
    if value is None or value == "":
        return None
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return None


def clean_number(value):

    if not value:
        return 0.0

    value = (
        value.replace("$", "")
        .replace(",", "")
        .replace("%", "")
        .replace("(", "-")
        .replace(")", "")
        .strip()
    )

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
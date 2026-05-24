def validate_int(value, max_value):
    try:
        v = int(value)
        if v < 0 or v >= max_value:
            return None
        return v
    except:
        return None


def validate_code(value, mapping):
    value = value.strip()
    return value if value in mapping else None


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
    except:
        return 0.0
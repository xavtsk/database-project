class ValidationError(ValueError):
    """An invalid player action; return a useful message without changing state."""


def integer(value, name):
    if type(value) is not int:
        raise ValidationError(f"{name} must be an integer")
    return value


def text_name(value, maximum):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= maximum:
        raise ValidationError(f"Name must contain 1–{maximum} characters")
    return value.strip()

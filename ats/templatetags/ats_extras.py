from django import template

register = template.Library()

@register.filter
def filter_status_count(applications, status):
    """Counts the number of applications with a specific status."""
    return applications.filter(status=status).count()

@register.filter
def percent(value, total):
    """Calculates percentage. total=0 acts as a multiplier of 100 for decimals."""
    try:
        if total == 0:
            return f"{float(value) * 100:.1f}%"
        return f"{(float(value) / float(total)) * 100:.1f}%"
    except (ValueError, ZeroDivisionError, TypeError):
        return "0%"

@register.filter
def subtract(value, arg):
    """Subtracts the arg from the value."""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return value

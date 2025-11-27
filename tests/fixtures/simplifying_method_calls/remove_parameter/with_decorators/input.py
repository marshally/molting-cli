"""Example code for remove-parameter with decorators."""


def cache_result(func):
    """Decorator to cache results."""
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


class ReportGenerator:
    def __init__(self):
        self.data = []

    @cache_result
    def generate_report(self, title, format_type, unused_param):
        """Generate a report with the given title."""
        return f"{title} report in {format_type}"

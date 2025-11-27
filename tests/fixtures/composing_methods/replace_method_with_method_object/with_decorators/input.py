"""Example code for replace-method-with-method-object with decorators."""


def log_call(func):
    """Custom decorator for logging method calls."""

    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        return func(*args, **kwargs)

    return wrapper


class Report:
    def __init__(self, data, title):
        self.data = data
        self.title = title
        self.format = "pdf"

    @log_call
    def generate_summary(self):
        """Complex method that generates a summary report."""
        # Calculate statistics
        total = sum(item.value for item in self.data)
        average = total / len(self.data) if self.data else 0
        maximum = max(item.value for item in self.data) if self.data else 0
        minimum = min(item.value for item in self.data) if self.data else 0

        # Format the summary
        summary = f"Report: {self.title}\n"
        summary += f"Total: {total}\n"
        summary += f"Average: {average}\n"
        summary += f"Max: {maximum}\n"
        summary += f"Min: {minimum}\n"

        return summary

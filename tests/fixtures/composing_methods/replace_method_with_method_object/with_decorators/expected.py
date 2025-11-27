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
        return Generate_summary(self).compute()


class Generate_summary:
    def __init__(self, account):
        self.account = account

    def compute(self):
        """Complex method that generates a summary report."""
        # Calculate statistics
        total = sum(item.value for item in self.account.data)
        average = total / len(self.account.data) if self.account.data else 0
        maximum = max(item.value for item in self.account.data) if self.account.data else 0
        minimum = min(item.value for item in self.account.data) if self.account.data else 0

        # Format the summary
        summary = f"Report: {self.account.title}\n"
        summary += f"Total: {total}\n"
        summary += f"Average: {average}\n"
        summary += f"Max: {maximum}\n"
        summary += f"Min: {minimum}\n"

        return summary

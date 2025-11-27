"""Expected output after extract-function with decorators."""


def log_call(func):
    """Custom decorator for logging method calls."""

    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        return func(*args, **kwargs)

    return wrapper


def format_email_address(recipient):
    return recipient.strip().lower()


class EmailService:
    @log_call
    def send_email(self, recipient, subject, body):
        """Send an email to a recipient."""
        formatted_email = format_email_address(recipient)
        print(f"Sending email to {formatted_email}")
        print(f"Subject: {subject}")
        print(f"Body: {body}")
        return formatted_email

    @staticmethod
    def validate_email(email):
        """Validate an email address."""
        # Extract domain from email
        domain = email.split("@")[1] if "@" in email else ""
        return len(domain) > 0

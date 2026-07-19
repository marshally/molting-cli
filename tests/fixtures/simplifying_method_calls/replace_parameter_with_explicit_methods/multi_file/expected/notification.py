"""Notification system for sending messages."""


class Notification:
    """Handles sending notifications via different channels."""

    def __init__(self, config):
        self.config = config
        self.sent_count = 0

    def send_email(self, recipient, message):
        """Send an email notification.

        Args:
            recipient: Email address of the recipient
            message: Message content to send

        Returns:
            True if sent successfully, False otherwise
        """
        self.sent_count += 1
        return self._send_email(recipient, message)

    def send_sms(self, recipient, message):
        """Send an SMS notification.

        Args:
            recipient: Phone number of the recipient
            message: Message content to send

        Returns:
            True if sent successfully, False otherwise
        """
        self.sent_count += 1
        return self._send_sms(recipient, message)

    def _send_email(self, email_address, body):
        """Send an email notification."""
        print(f"Sending email to {email_address}: {body}")
        # Actual email sending logic would go here
        return True

    def _send_sms(self, phone_number, body):
        """Send an SMS notification."""
        print(f"Sending SMS to {phone_number}: {body}")
        # Actual SMS sending logic would go here
        return True

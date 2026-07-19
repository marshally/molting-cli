"""Notification system for sending messages."""


class Notification:
    """Handles sending notifications via different channels."""

    def __init__(self, config):
        self.config = config
        self.sent_count = 0

    def send(self, type, recipient, message):
        """Send a notification via the specified type.

        Args:
            type: Type of notification ("email" or "sms")
            recipient: Recipient identifier (email address or phone number)
            message: Message content to send

        Returns:
            True if sent successfully, False otherwise
        """
        self.sent_count += 1

        if type == "email":
            return self._send_email(recipient, message)
        elif type == "sms":
            return self._send_sms(recipient, message)
        else:
            raise ValueError(f"Unknown notification type: {type}")

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

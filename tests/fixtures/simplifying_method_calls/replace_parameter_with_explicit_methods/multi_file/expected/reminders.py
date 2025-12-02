"""Reminder system for user notifications."""

from notification import Notification


class ReminderService:
    """Manages reminders sent to users."""

    def __init__(self):
        self.notifier = Notification(config={"provider": "twilio"})

    def send_appointment_reminder(self, phone_number, appointment_time):
        """Send appointment reminder via SMS.

        Args:
            phone_number: User's phone number
            appointment_time: Time of appointment

        Returns:
            True if reminder sent successfully
        """
        message = f"Reminder: Your appointment is scheduled for {appointment_time}"
        return self.notifier.send_sms(phone_number, message)

    def send_payment_reminder(self, phone_number, amount_due):
        """Send payment reminder via SMS.

        Args:
            phone_number: User's phone number
            amount_due: Amount of payment due

        Returns:
            True if reminder sent successfully
        """
        message = f"Payment reminder: ${amount_due:.2f} is due soon"
        return self.notifier.send_sms(phone_number, message)

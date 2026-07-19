"""Alert system for critical notifications."""

from notification import Notification


class AlertSystem:
    """Manages critical alerts sent to administrators."""

    def __init__(self):
        self.notifier = Notification(config={"provider": "default"})
        self.alert_history = []

    def send_critical_alert(self, admin_email, alert_message):
        """Send a critical alert to an administrator via email.

        Args:
            admin_email: Administrator's email address
            alert_message: Alert message content

        Returns:
            True if alert sent successfully
        """
        success = self.notifier.send("email", admin_email, alert_message)
        if success:
            self.alert_history.append({
                "type": "email",
                "recipient": admin_email,
                "message": alert_message
            })
        return success

    def send_security_notification(self, admin_email, details):
        """Send a security notification via email.

        Args:
            admin_email: Administrator's email address
            details: Security incident details

        Returns:
            True if notification sent
        """
        message = f"Security Alert: {details}"
        return self.notifier.send("email", admin_email, message)

class EmailService:
    def __init__(self):
        self.from_address = "noreply@example.com"
        self.smtp_server = "smtp.example.com"
        self.default_subject = "Notification"

    def send_email(self, to_address, subject, body):
        message = f"From: {self.from_address}\n"
        message += f"To: {to_address}\n"
        message += f"Subject: {subject or self.default_subject}\n\n"
        message += body
        return message

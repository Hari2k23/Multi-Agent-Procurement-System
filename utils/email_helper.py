import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import re
from dotenv import load_dotenv

load_dotenv()

class EmailHelper:
    """Gmail SMTP email sender with validation."""

    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.sender_email = os.getenv('GMAIL_USER')
        self.sender_password = os.getenv('GMAIL_APP_PASSWORD')

        if not self.sender_email or not self.sender_password:
            raise ValueError("Gmail credentials not found in .env file. Set GMAIL_USER and GMAIL_APP_PASSWORD")

    def _validate_email(self, email: str) -> bool:
        """Validate email address format using regex."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_pattern, email) is not None

    def send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send email via Gmail SMTP."""
        if not self._validate_email(to_email):
            print(f"Invalid email format: {to_email}")
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = to_email
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.send_message(msg)
            server.quit()

            print(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            print(f"Failed to send email to {to_email}: {e}")
            return False

    def send_bulk_email(self, recipients: list, subject: str, body: str) -> dict:
        """Send same email to multiple recipients."""
        results = {
            'success': [],
            'failed': []
        }

        for email in recipients:
            if self.send_email(email, subject, body):
                results['success'].append(email)
            else:
                results['failed'].append(email)

        return results

if __name__ == "__main__":
    print("Testing Email Helper\n")

    try:
        helper = EmailHelper()
        print(f"Gmail User: {helper.sender_email}")
        print("Gmail App Password: ****** (loaded)")

        print("\nTesting email validation:")
        test_emails = [
            'valid@example.com',
            'invalid.email',
            'another@valid.co.in',
            'bad@email',
            'test.user+filter@domain.com'
        ]

        for test_email in test_emails:
            is_valid = helper._validate_email(test_email)
            print(f"  {test_email}: {'✓ VALID' if is_valid else '✗ INVALID'}")

        print("\nEmail helper initialized successfully")

    except ValueError as e:
        print(f"Error: {e}")
        print("\nTo use email functionality, add to your .env file:")
        print("GMAIL_USER=your.email@gmail.com")
        print("GMAIL_APP_PASSWORD=your_app_password")
        
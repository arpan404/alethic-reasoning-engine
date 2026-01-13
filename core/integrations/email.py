"""Email integration utilities for sending emails."""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Email service for sending emails via SMTP."""
    
    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
    ):
        """
        Initialize email service.
        
        Args:
            smtp_host: SMTP server host
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_password: SMTP password
            from_email: Default sender email
            from_name: Default sender name
        """
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.getenv("SMTP_USER")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
        self.from_email = from_email or os.getenv("SMTP_FROM_EMAIL", self.smtp_user)
        self.from_name = from_name or os.getenv("SMTP_FROM_NAME", "ATS")
    
    def send_email(
        self,
        to_email: str | List[str],
        subject: str,
        body: str,
        html: bool = False,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[str | Path]] = None,
        reply_to: Optional[str] = None,
    ) -> bool:
        """
        Send an email.
        
        Args:
            to_email: Recipient email address(es)
            subject: Email subject
            body: Email body
            html: Whether body is HTML
            cc: CC recipients
            bcc: BCC recipients
            attachments: List of file paths to attach
            reply_to: Reply-to email address
            
        Returns:
            True if email sent successfully
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            
            # Handle multiple recipients
            if isinstance(to_email, list):
                msg['To'] = ", ".join(to_email)
                recipients = to_email
            else:
                msg['To'] = to_email
                recipients = [to_email]
            
            msg['Subject'] = subject
            
            if cc:
                msg['Cc'] = ", ".join(cc)
                recipients.extend(cc)
            
            if bcc:
                recipients.extend(bcc)
            
            if reply_to:
                msg['Reply-To'] = reply_to
            
            # Attach body
            if html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # Attach files
            if attachments:
                for attachment_path in attachments:
                    self._attach_file(msg, Path(attachment_path))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg, from_addr=self.from_email, to_addrs=recipients)
            
            logger.info(f"Email sent to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def _attach_file(self, msg: MIMEMultipart, file_path: Path):
        """Attach a file to the email message."""
        with open(file_path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
        
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename= {file_path.name}'
        )
        
        msg.attach(part)
    
    def send_template_email(
        self,
        to_email: str | List[str],
        template_name: str,
        context: dict,
        subject: str,
        **kwargs
    ) -> bool:
        """
        Send an email using a template.
        
        Args:
            to_email: Recipient email address(es)
            template_name: Name of the email template
            context: Template context variables
            subject: Email subject
            **kwargs: Additional arguments passed to send_email
            
        Returns:
            True if email sent successfully
        """
        # TODO: Implement template rendering
        # For now, just use plain text
        body = self._render_template(template_name, context)
        return self.send_email(to_email, subject, body, html=True, **kwargs)
    
    def _render_template(self, template_name: str, context: dict) -> str:
        """Render email template with context."""
        # TODO: Implement proper template rendering (Jinja2)
        # For now, return placeholder
        return f"Template: {template_name}\nContext: {context}"


# Pre-configured email templates
class EmailTemplates:
    """Pre-configured email templates."""
    
    @staticmethod
    def welcome_email(user_name: str, login_url: str) -> dict:
        """Welcome email template."""
        return {
            'subject': 'Welcome to ATS!',
            'body': f"""
                <html>
                <body>
                    <h2>Welcome {user_name}!</h2>
                    <p>Thank you for joining our ATS platform.</p>
                    <p>You can login here: <a href="{login_url}">{login_url}</a></p>
                    <p>Best regards,<br>The ATS Team</p>
                </body>
                </html>
            """,
            'html': True
        }
    
    @staticmethod
    def password_reset_email(user_name: str, reset_url: str) -> dict:
        """Password reset email template."""
        return {
            'subject': 'Password Reset Request',
            'body': f"""
                <html>
                <body>
                    <h2>Hi {user_name},</h2>
                    <p>We received a request to reset your password.</p>
                    <p>Click here to reset: <a href="{reset_url}">{reset_url}</a></p>
                    <p>This link will expire in 1 hour.</p>
                    <p>If you didn't request this, please ignore this email.</p>
                    <p>Best regards,<br>The ATS Team</p>
                </body>
                </html>
            """,
            'html': True
        }
    
    @staticmethod
    def interview_invitation(
        candidate_name: str,
        position: str,
        interview_date: str,
        interview_time: str,
        meeting_link: Optional[str] = None
    ) -> dict:
        """Interview invitation email template."""
        meeting_info = f'<p>Meeting Link: <a href="{meeting_link}">{meeting_link}</a></p>' if meeting_link else ''
        
        return {
            'subject': f'Interview Invitation - {position}',
            'body': f"""
                <html>
                <body>
                    <h2>Hi {candidate_name},</h2>
                    <p>We're excited to invite you for an interview for the {position} position.</p>
                    <p><strong>Date:</strong> {interview_date}</p>
                    <p><strong>Time:</strong> {interview_time}</p>
                    {meeting_info}
                    <p>Please confirm your availability.</p>
                    <p>Best regards,<br>The Hiring Team</p>
                </body>
                </html>
            """,
            'html': True
        }
    
    @staticmethod
    def application_received(candidate_name: str, position: str) -> dict:
        """Application received confirmation email."""
        return {
            'subject': f'Application Received - {position}',
            'body': f"""
                <html>
                <body>
                    <h2>Hi {candidate_name},</h2>
                    <p>Thank you for applying for the {position} position.</p>
                    <p>We've received your application and will review it shortly.</p>
                    <p>We'll be in touch soon!</p>
                    <p>Best regards,<br>The Hiring Team</p>
                </body>
                </html>
            """,
            'html': True
        }


# Global email service instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create global email service instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service

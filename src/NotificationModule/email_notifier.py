#!/usr/bin/env python3
"""
Email Notification Module

Simple functions for sending error notifications to developers when 
important errors occur in the bot system.
"""

import smtplib
import traceback
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv


def send_error_email(error_message: str, 
                    error_location: str, 
                    additional_info: Optional[Dict[str, Any]] = None) -> bool:
    """
    Send an error notification email to the developer.
    
    Args:
        error_message: The error message to send
        error_location: Where the error occurred (function, module, etc.)
        additional_info: Optional dictionary with additional error context
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # Load environment variables
        load_dotenv("bot.env")

        # Get email configuration from environment
        smtp_server = os.getenv('SMTP_SERVER')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        sender_email = os.getenv('SENDER_EMAIL')
        sender_password = os.getenv('SENDER_PASSWORD')
        dev_email = os.getenv('DEV_EMAIL')

        # Check if all required values are present
        if not all([smtp_server, sender_email, sender_password, dev_email]):
            print("[EMAIL] Missing email configuration in environment variables")
            return False

        # Create email message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = dev_email
        msg['Subject'] = f"Bot Error Alert - {error_location}"

        # Create email body
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        body = f"""
Bot Error Alert

Timestamp: {timestamp}
Location: {error_location}
Error Message: {error_message}

"""

        # Add additional information if provided
        if additional_info:
            body += "Additional Information:\n"
            for key, value in additional_info.items():
                body += f"  {key}: {value}\n"
            body += "\n"

        # Add stack trace if available
        stack_trace = traceback.format_exc()
        if stack_trace and stack_trace != "NoneType: None\n":
            body += f"Stack Trace:\n{stack_trace}\n"

        body += """
This is an automated error notification from the Bot system.
Please investigate and resolve the issue.

Best regards,
Bot Monitoring System
"""

        # Attaching and sending email
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Enable encryption
        server.login(sender_email, sender_password)

        text = msg.as_string()
        server.sendmail(sender_email, dev_email, text)
        server.quit()

        print(f"[EMAIL SENT] Error notification sent to {dev_email}")
        return True

    except Exception as e:
        print(f"[EMAIL FAILED] Failed to send error email: {str(e)}")
        return False


def notify_error(error_message: str, 
                error_location: str,
                additional_info: Optional[Dict[str, Any]] = None) -> None:
    """
    Send error notification email. Safe to call - won't raise exceptions.

    Args:
        error_message: The error message to send
        error_location: Where the error occurred
        additional_info: Optional dictionary with additional error context
    """
    try:
        send_error_email(error_message, error_location, additional_info)
    except Exception as e:
        print(f"[EMAIL ERROR] Exception in notify_error: {e}")

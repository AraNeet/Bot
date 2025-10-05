

from typing import Dict, Any, Optional
from src.notification_module.email_sender import send_error_email


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

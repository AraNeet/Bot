# Notification Module for error reporting and alerts

"""
Simple functions for sending error notifications to developers when
important errors occur in the bot system.
"""

from .error_notifier import notify_error

__all__ = ['notify_error']
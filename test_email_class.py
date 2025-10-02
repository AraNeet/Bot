#!/usr/bin/env python3
"""
Test script for the simplified email notification functions.
Demonstrates how to use the function-based email notification system.
"""

from src.NotificationModule import email_notifier
from src.StartupModule import loader

def test_email_functions():
    """Test the email notification functions."""
    print("Testing email notification functions...")
    
    # Check if configured
    if loader.is_email_configured("config.json"):
        print("✅ Email notifications are configured and ready")
        
        # Test sending an error notification
        print("\nTesting error notification...")
        success = email_notifier.send_error_email(
            error_message="This is a test error from the function-based system",
            error_location="test_email_functions.py",
            additional_info={
                "test_type": "function_test",
                "method": "send_error_email"
            }
        )
        
        if success:
            print("✅ Error email sent successfully")
        else:
            print("❌ Failed to send error email")
        
        # Test the convenience function
        print("\nTesting convenience function...")
        email_notifier.notify_error(
            "This is a test using notify_error function",
            "test_email_functions.py"
        )
        print("✅ Convenience function called")
        
    else:
        print("❌ Email notifications are not configured properly")
        print("Check your config.json email_notifications section")
    
    print("\nEmail notification function test completed!")

def demonstrate_usage():
    """Demonstrate how to use the email functions in different scenarios."""
    print("\n" + "="*50)
    print("USAGE EXAMPLES")
    print("="*50)
    
    # Example 1: Direct function calls
    print("\n1. Direct function usage:")
    if loader.is_email_configured():
        email_notifier.notify_error("Direct function test", "example.function")
    
    # Example 2: In error handling
    print("\n2. Error handling usage:")
    def some_function_that_might_fail():
        try:
            # Simulate some work that might fail
            raise ValueError("Something went wrong!")
        except Exception as e:
            email_notifier.notify_error(str(e), "some_function_that_might_fail")
    
    some_function_that_might_fail()
    
    # Example 3: With additional info
    print("\n3. With additional context:")
    email_notifier.notify_error(
        "Database connection failed", 
        "database.connect",
        {"retry_count": 3, "timeout": 30}
    )
    
    print("\nUsage examples completed!")

if __name__ == "__main__":
    test_email_functions()
    demonstrate_usage()

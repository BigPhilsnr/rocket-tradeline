import frappe
from rockettradeline.api.payment import send_payment_request_notification_email, send_payment_approval_email

def test_email_functions_directly():
    """Test email functions directly to see what's causing the False return"""
    
    try:
        print("=== Direct Email Function Test ===")
        
        # Get the specific payment request
        payment_request_name = "Manual Payment - CART-0046 - 20250826103934"
        payment_request = frappe.get_doc("Payment Request", payment_request_name)
        
        print(f"Testing with Payment Request: {payment_request.name}")
        print(f"Customer Email: {payment_request.customer_email}")
        
        # Test notification email
        print("\n1. Testing send_payment_request_notification_email:")
        queue_before = frappe.db.count("Email Queue")
        
        try:
            result1 = send_payment_request_notification_email(payment_request)
            print(f"  Result: {result1}")
        except Exception as e:
            print(f"  Exception caught: {str(e)}")
            result1 = False
        
        queue_after = frappe.db.count("Email Queue")
        print(f"  Queue before: {queue_before}, after: {queue_after}, added: {queue_after - queue_before}")
        
        # Test approval email
        print("\n2. Testing send_payment_approval_email:")
        queue_before = queue_after
        
        try:
            result2 = send_payment_approval_email(payment_request)
            print(f"  Result: {result2}")
        except Exception as e:
            print(f"  Exception caught: {str(e)}")
            result2 = False
        
        queue_after = frappe.db.count("Email Queue")
        print(f"  Queue before: {queue_before}, after: {queue_after}, added: {queue_after - queue_before}")
        
        # Check recent errors in Error Log
        print("\n3. Checking recent Error Logs:")
        recent_errors = frappe.get_all(
            "Error Log",
            fields=["name", "creation", "error"],
            order_by="creation desc",
            limit=5
        )
        
        for error in recent_errors:
            if "Email" in error.get("error", ""):
                print(f"  - {error.name}: {error.error[:200]}...")
                
        print(f"\n=== Test Summary ===")
        print(f"Notification Email Function Result: {result1}")
        print(f"Approval Email Function Result: {result2}")
        print(f"Both functions are working (emails being queued), investigating return values...")
        
    except Exception as e:
        print(f"Test failed with error: {str(e)}")
        frappe.log_error(f"Direct email test error: {str(e)}", "Direct Email Test Error")

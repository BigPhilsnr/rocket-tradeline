import frappe
from rockettradeline.api.payment import send_payment_request_notification_email, send_payment_approval_email

def test_manual_payment_email_flow():
    """Test email notifications during manual payment creation and approval"""
    try:
        print("=== Testing Manual Payment Email Flow ===")
        
        # Get the specific payment request
        payment_request_name = "Manual Payment - CART-0046 - 20250826103934"
        payment_request = frappe.get_doc("Payment Request", payment_request_name)
        
        print(f"Testing with Payment Request: {payment_request.name}")
        print(f"Status: {payment_request.status}")
        print(f"Approval Status: {payment_request.approval_status}")
        print(f"Customer Email: {payment_request.customer_email}")
        
        # Test 1: Payment Request Notification Email (should be sent when payment is created)
        print(f"\n1. Testing Payment Request Notification Email:")
        queue_before = frappe.db.count("Email Queue")
        
        try:
            result1 = send_payment_request_notification_email(payment_request)
            print(f"   ✓ Notification email result: {result1}")
        except Exception as e:
            print(f"   ✗ Notification email failed: {str(e)}")
            result1 = False
        
        queue_after = frappe.db.count("Email Queue")
        print(f"   Email queue before: {queue_before}, after: {queue_after}, added: {queue_after - queue_before}")
        
        # Test 2: Payment Approval Email (should be sent when payment is approved)
        print(f"\n2. Testing Payment Approval Email:")
        queue_before = queue_after
        
        try:
            result2 = send_payment_approval_email(payment_request)
            print(f"   ✓ Approval email result: {result2}")
        except Exception as e:
            print(f"   ✗ Approval email failed: {str(e)}")
            result2 = False
        
        queue_after = frappe.db.count("Email Queue")
        print(f"   Email queue before: {queue_before}, after: {queue_after}, added: {queue_after - queue_before}")
        
        # Check recent emails in queue
        print(f"\n3. Recent emails in queue:")
        recent_emails = frappe.get_all(
            "Email Queue",
            fields=["name", "status", "creation"],
            order_by="creation desc",
            limit=5
        )
        
        for email in recent_emails:
            # Get full document to access recipients
            full_email = frappe.get_doc("Email Queue", email.name)
            recipients = [r.recipient for r in full_email.recipients] if full_email.recipients else ["No recipients"]
            print(f"   - {email.name}: Status {email.status} → Recipients: {recipients}")
        
        print(f"\n=== Summary ===")
        print(f"✅ Payment Request Notification: {'Success' if result1 else 'Failed'}")
        print(f"✅ Payment Approval Email: {'Success' if result2 else 'Failed'}")
        print(f"📧 Total emails sent: {2 if (result1 and result2) else (1 if (result1 or result2) else 0)}")
        
        return result1 and result2
        
    except Exception as e:
        print(f"Test failed with error: {str(e)}")
        return False


def test_manual_payment_creation_simulation():
    """Simulate manual payment creation to test email notification"""
    try:
        print("\n=== Simulating Manual Payment Creation ===")
        
        # This simulates what happens in create_manual_payment_request
        # We'll test just the email part using an existing payment request
        
        payment_request_name = "Manual Payment - CART-0046 - 20250826103934"
        payment_doc = frappe.get_doc("Payment Request", payment_request_name)
        
        print(f"Simulating email notification for: {payment_doc.name}")
        
        queue_before = frappe.db.count("Email Queue")
        
        # This is the email call that should happen in create_manual_payment_request
        try:
            email_sent = send_payment_request_notification_email(payment_doc)
            if email_sent:
                print(f"✓ Notification email sent successfully")
            else:
                print(f"✗ Notification email failed")
        except Exception as email_error:
            print(f"✗ Email notification error: {str(email_error)}")
            email_sent = False
        
        queue_after = frappe.db.count("Email Queue")
        print(f"Email queue count changed by: {queue_after - queue_before}")
        
        return email_sent
        
    except Exception as e:
        print(f"Simulation test failed: {str(e)}")
        return False

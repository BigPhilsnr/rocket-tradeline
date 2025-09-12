import frappe
from rockettradeline.api.payment import send_payment_request_notification_email

def test_manual_payment_creation_email():
    """Test if email notification works during manual payment creation"""
    try:
        print("=== Testing Manual Payment Creation Email ===")
        
        # Use the existing payment request for testing
        payment_request_name = "Manual Payment - CART-0046 - 20250826103934"
        payment_doc = frappe.get_doc("Payment Request", payment_request_name)
        
        print(f"Testing notification email for: {payment_doc.name}")
        print(f"Customer: {payment_doc.customer_email}")
        print(f"Amount: ${payment_doc.total_amount}")
        
        # Check email queue before
        queue_before = frappe.db.count("Email Queue")
        print(f"Email queue count before: {queue_before}")
        
        # Test the email notification function
        try:
            result = send_payment_request_notification_email(payment_doc)
            print(f"✓ Email notification result: {result}")
        except Exception as e:
            print(f"✗ Email notification failed: {str(e)}")
            return False
        
        # Check email queue after
        queue_after = frappe.db.count("Email Queue")
        print(f"Email queue count after: {queue_after}")
        print(f"Emails added: {queue_after - queue_before}")
        
        if queue_after > queue_before:
            # Get the latest email details
            latest_email = frappe.get_all(
                "Email Queue",
                fields=["name", "status"],
                order_by="creation desc",
                limit=1
            )[0]
            
            full_email = frappe.get_doc("Email Queue", latest_email.name)
            recipients = [r.recipient for r in full_email.recipients] if full_email.recipients else []
            
            print(f"Latest email:")
            print(f"  - ID: {latest_email.name}")
            print(f"  - Status: {latest_email.status}")
            print(f"  - Recipients: {recipients}")
            
            if "info@rockettradeline.com" in recipients:
                print("✓ SUCCESS: Email sent to admin successfully")
                return True
            else:
                print("✗ ERROR: Email not sent to correct recipient")
                return False
        else:
            print("✗ ERROR: No email was added to queue")
            return False
            
    except Exception as e:
        print(f"Test failed: {str(e)}")
        return False

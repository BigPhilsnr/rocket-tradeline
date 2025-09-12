import frappe
from rockettradeline.api.payment import approve_manual_payment

def test_manual_payment_approval():
    """Test manual payment approval with email sending"""
    try:
        print("=== Testing Manual Payment Approval with Email ===")
        
        # Get the specific payment request
        payment_request_name = "Manual Payment - CART-0046 - 20250826103934"
        payment_request = frappe.get_doc("Payment Request", payment_request_name)
        
        print(f"Testing with Payment Request: {payment_request.name}")
        print(f"Current Status: {payment_request.status}")
        print(f"Current Approval Status: {getattr(payment_request, 'approval_status', 'Not Set')}")
        print(f"Customer Email: {payment_request.customer_email}")
        
        # Check email queue before
        queue_before = frappe.db.count("Email Queue")
        print(f"\nEmail Queue count before approval: {queue_before}")
        
        # Test the approval function
        print(f"\nTesting approval function...")
        
        # First, reset the approval status to test
        payment_request.approval_status = "Pending Approval"
        payment_request.save(ignore_permissions=True)
        frappe.db.commit()
        
        # Now test the approval
        result = approve_manual_payment(
            payment_request_id=payment_request.name,
            approval_action="approve"
        )
        
        print(f"Approval result: {result}")
        
        # Check email queue after
        queue_after = frappe.db.count("Email Queue")
        print(f"Email Queue count after approval: {queue_after}")
        print(f"Emails added: {queue_after - queue_before}")
        
        # Check recent emails
        if queue_after > queue_before:
            recent_emails = frappe.get_all(
                "Email Queue",
                fields=["name", "status", "creation"],
                order_by="creation desc",
                limit=2
            )
            
            print(f"\nRecent emails:")
            for email in recent_emails:
                full_email = frappe.get_doc("Email Queue", email.name)
                recipients = [r.recipient for r in full_email.recipients] if full_email.recipients else ["No recipients"]
                print(f"  - {email.name}: Status {email.status} → Recipients: {recipients}")
        
        # Check the updated payment request
        updated_payment = frappe.get_doc("Payment Request", payment_request.name)
        print(f"\nUpdated Payment Request:")
        print(f"  - Status: {updated_payment.status}")
        print(f"  - Approval Status: {updated_payment.approval_status}")
        print(f"  - Approved By: {getattr(updated_payment, 'approved_by', 'Not Set')}")
        print(f"  - Approved At: {getattr(updated_payment, 'approved_at', 'Not Set')}")
        print(f"  - Transaction ID: {getattr(updated_payment, 'transaction_id', 'Not Set')}")
        
        return True
        
    except Exception as e:
        print(f"Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

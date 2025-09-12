import frappe
from rockettradeline.api.auth import get_email_header, get_email_footer

def test_minimal_payment_notification():
    """Test payment notification with minimal exception handling"""
    try:
        print("=== Minimal Payment Notification Test ===")
        
        # Get the payment request
        payment_request_name = "Manual Payment - CART-0046 - 20250826103934"
        payment_request_doc = frappe.get_doc("Payment Request", payment_request_name)
        
        print(f"Testing with: {payment_request_doc.name}")
        
        # Get header and footer
        email_header = get_email_header()
        email_footer = get_email_footer("info@rockettradeline.com")
        
        # Build message with safe field access
        payment_details = f"""{email_header}
        <h3 style="color: #374151; margin: 0 0 20px 0;">New Payment Request Created</h3>
        <div style="background-color: #f9fafb; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
            <p style="margin: 5px 0;"><strong>Payment Request ID:</strong> {payment_request_doc.name}</p>
            <p style="margin: 5px 0;"><strong>Customer:</strong> {getattr(payment_request_doc, 'customer_name', 'N/A')} ({payment_request_doc.customer_email})</p>
            <p style="margin: 5px 0;"><strong>Payment Method:</strong> {payment_request_doc.payment_method}</p>
            <p style="margin: 5px 0;"><strong>Amount:</strong> ${payment_request_doc.amount:.2f}</p>
            <p style="margin: 5px 0;"><strong>Total Amount:</strong> ${payment_request_doc.total_amount:.2f}</p>
            <p style="margin: 5px 0;"><strong>Cart ID:</strong> {payment_request_doc.cart_id}</p>
            <p style="margin: 5px 0;"><strong>Status:</strong> {payment_request_doc.status}</p>
            <p style="margin: 5px 0;"><strong>Created At:</strong> {getattr(payment_request_doc, 'created_at', payment_request_doc.creation)}</p>
        </div>
        {email_footer}"""
        
        # Send email without exception handling
        queue_before = frappe.db.count("Email Queue")
        print(f"Queue before: {queue_before}")
        
        result = frappe.sendmail(
            recipients=["info@rockettradeline.com"],
            subject=f"Minimal Test - {payment_request_doc.name}",
            message=payment_details,
            header=["New Payment Request Notification"],
            delayed=False
        )
        
        queue_after = frappe.db.count("Email Queue")
        print(f"Queue after: {queue_after}")
        print(f"Emails added: {queue_after - queue_before}")
        print(f"✓ SUCCESS: Email sent/queued successfully")
        print(f"Result: {result}")
        
        return True
        
    except Exception as e:
        print(f"✗ EXCEPTION: {str(e)}")
        print(f"Exception type: {type(e)}")
        import traceback
        print(f"Traceback:")
        traceback.print_exc()
        return False

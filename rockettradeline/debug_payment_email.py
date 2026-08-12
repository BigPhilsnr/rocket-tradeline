import frappe
from rockettradeline.api.auth import get_email_header, get_email_footer

def debug_payment_email_function():
    """Debug the exact issue in the payment email function"""
    try:
        print("=== Debug Payment Email Function ===")
        
        # Get the payment request
        payment_request_name = "Manual Payment - CART-0046 - 20250826103934"
        payment_request_doc = frappe.get_doc("Payment Request", payment_request_name)
        
        print(f"Payment Request loaded: {payment_request_doc.name}")
        
        # Step 1: Test getting header and footer
        print("\n1. Getting email header and footer...")
        try:
            email_header = get_email_header()
            email_footer = get_email_footer("info@rockettradeline.com")
            print("✓ Header and footer retrieved successfully")
        except Exception as e:
            print(f"✗ Header/footer error: {str(e)}")
            return False
        
        # Step 2: Test accessing payment request fields
        print("\n2. Testing payment request field access...")
        try:
            print(f"  - name: {payment_request_doc.name}")
            print(f"  - customer_email: {getattr(payment_request_doc, 'customer_email', 'NOT FOUND')}")
            print(f"  - customer_name: {getattr(payment_request_doc, 'customer_name', 'NOT FOUND')}")
            print(f"  - payment_method: {getattr(payment_request_doc, 'payment_method', 'NOT FOUND')}")
            print(f"  - amount: {getattr(payment_request_doc, 'amount', 'NOT FOUND')}")
            print(f"  - total_amount: {getattr(payment_request_doc, 'total_amount', 'NOT FOUND')}")
            print(f"  - cart_id: {getattr(payment_request_doc, 'cart_id', 'NOT FOUND')}")
            print(f"  - status: {getattr(payment_request_doc, 'status', 'NOT FOUND')}")
            print(f"  - created_at: {getattr(payment_request_doc, 'created_at', 'NOT FOUND')}")
            print("✓ All payment request fields accessible")
        except Exception as e:
            print(f"✗ Field access error: {str(e)}")
            return False
        
        # Step 3: Test building the email content
        print("\n3. Building email content...")
        try:
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
        
        <h4 style="color: #374151; margin: 20px 0 15px 0;">Action Required:</h4>
        <p style="color: #6b7280; line-height: 1.6; margin: 0 0 20px 0;">
            Please log in to the admin portal to review and approve this payment request.
        </p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="https://rocket-app.tiberbuhealth.com/app/payment-request/{payment_request_doc.name}" 
               style="background-color: #17B26A; color: white; padding: 12px 24px; text-decoration: none; 
                      border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">
                View Payment Request
            </a>
        </div>
        {email_footer}"""
            
            print("✓ Email content built successfully")
            print(f"Content length: {len(payment_details)}")
        except Exception as e:
            print(f"✗ Content building error: {str(e)}")
            return False
        
        # Step 4: Test sending the email
        print("\n4. Testing email sending...")
        queue_before = frappe.db.count("Email Queue")
        
        try:
            result = frappe.sendmail(
                recipients=["info@rockettradeline.com"],
                subject=f"Debug Payment Request - {payment_request_doc.name}",
                message=payment_details,
                header=["New Payment Request Notification"],
                delayed=False
            )
            
            queue_after = frappe.db.count("Email Queue")
            print(f"✓ Email sent successfully")
            print(f"  Result: {result}")
            print(f"  Emails added: {queue_after - queue_before}")
            return True
            
        except Exception as e:
            print(f"✗ Email sending error: {str(e)}")
            return False
        
    except Exception as e:
        print(f"Debug test failed: {str(e)}")
        frappe.log_error(f"Debug payment email error: {str(e)}", "Debug Payment Email Error")
        return False


def test_updated_payment_notification(payment_request_name=None):
    """
    Trigger the real (fixed) send_payment_request_notification_email() against an
    actual Payment Request so the resulting Email Queue entry can be inspected to
    confirm the tradeline_info context is now populated correctly.
    """
    from rockettradeline.api.payment import send_payment_request_notification_email

    if not payment_request_name:
        payment_request_name = frappe.db.get_value(
            "Payment Request", {}, "name", order_by="creation desc"
        )

    print(f"Using Payment Request: {payment_request_name}")
    payment_request_doc = frappe.get_doc("Payment Request", payment_request_name)

    queue_before = frappe.db.count("Email Queue")
    result = send_payment_request_notification_email(payment_request_doc)
    queue_after = frappe.db.count("Email Queue")

    print(f"send_payment_request_notification_email returned: {result}")
    print(f"Email Queue rows added: {queue_after - queue_before}")

    latest = frappe.db.sql(
        """
        SELECT name, creation FROM `tabEmail Queue`
        ORDER BY creation DESC LIMIT 1
        """,
        as_dict=True,
    )
    if latest:
        print(f"Latest Email Queue entry: {latest[0].name} at {latest[0].creation}")
    return result

import frappe
from rockettradeline.api.auth import get_email_header, get_email_footer

def test_header_footer_functions():
    """Test the header and footer functions independently"""
    try:
        print("=== Testing Email Header/Footer Functions ===")
        
        # Test 1: get_email_header
        print("1. Testing get_email_header():")
        try:
            header = get_email_header()
            print(f"  ✓ Header function works, length: {len(header)}")
            print(f"  Header preview: {header[:100]}...")
        except Exception as e:
            print(f"  ✗ Header function failed: {str(e)}")
            return False
        
        # Test 2: get_email_footer
        print("\n2. Testing get_email_footer():")
        try:
            footer = get_email_footer("test@example.com")
            print(f"  ✓ Footer function works, length: {len(footer)}")
            print(f"  Footer preview: {footer[:100]}...")
        except Exception as e:
            print(f"  ✗ Footer function failed: {str(e)}")
            return False
        
        # Test 3: Test manual email with header/footer
        print(f"\n3. Testing manual email with header/footer:")
        
        queue_before = frappe.db.count("Email Queue")
        
        email_content = f"""{header}
        <h3>Test Email with Header and Footer</h3>
        <p>This is a test email to check header and footer functionality.</p>
        {footer}"""
        
        try:
            result = frappe.sendmail(
                recipients=["info@rockettradeline.com"],
                subject="Test Email with Header/Footer",
                message=email_content,
                delayed=False
            )
            print(f"  ✓ Email with header/footer sent successfully")
            print(f"  Result: {result}")
        except Exception as e:
            print(f"  ✗ Email with header/footer failed: {str(e)}")
            return False
        
        queue_after = frappe.db.count("Email Queue")
        print(f"  Emails added: {queue_after - queue_before}")
        
        return True
        
    except Exception as e:
        print(f"Test failed: {str(e)}")
        frappe.log_error(f"Header/Footer test error: {str(e)}", "Header Footer Test Error")
        return False


def test_simplified_payment_notification():
    """Test payment notification without complex formatting"""
    try:
        print("\n=== Testing Simplified Payment Notification ===")
        
        # Get the payment request
        payment_request_name = "Manual Payment - CART-0046 - 20250826103934"
        payment_request = frappe.get_doc("Payment Request", payment_request_name)
        
        queue_before = frappe.db.count("Email Queue")
        
        # Simple email without header/footer
        simple_message = f"""
        <h3>New Payment Request Created</h3>
        <p><strong>Payment Request ID:</strong> {payment_request.name}</p>
        <p><strong>Amount:</strong> ${payment_request.total_amount:.2f}</p>
        <p><strong>Customer:</strong> {payment_request.customer_email}</p>
        <p><strong>Status:</strong> {payment_request.status}</p>
        """
        
        try:
            result = frappe.sendmail(
                recipients=["info@rockettradeline.com"],
                subject=f"Simple Payment Request - {payment_request.name}",
                message=simple_message,
                delayed=False
            )
            print(f"  ✓ Simplified notification sent successfully")
            print(f"  Result: {result}")
            
            queue_after = frappe.db.count("Email Queue")
            print(f"  Emails added: {queue_after - queue_before}")
            return True
            
        except Exception as e:
            print(f"  ✗ Simplified notification failed: {str(e)}")
            return False
        
    except Exception as e:
        print(f"Simplified test failed: {str(e)}")
        return False

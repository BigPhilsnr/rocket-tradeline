#!/usr/bin/env python3

import frappe
import sys
import os

# Add the path to the frappe-bench directory
sys.path.insert(0, '/home/erpuser/frappe-bench')

def test_payment_email_notifications():
    """Test payment email notifications with specific Payment Request"""
    
    # Initialize Frappe
    frappe.init(site='rocket-app.tiberbuhealth.com')
    frappe.connect()
    
    try:
        print("=== Testing Payment Email Notifications ===")
        print(f"Site: {frappe.local.site}")
        print(f"Current User: {frappe.session.user}")
        
        # Look for the specific Payment Request
        payment_request_name = "Manual Payment - CART-0046 - 20250826103934"
        
        print(f"\n1. Looking for Payment Request: {payment_request_name}")
        
        # Try to find the payment request
        try:
            payment_req = frappe.get_doc("Payment Request", payment_request_name)
            print(f"✓ Found Payment Request: {payment_req.name}")
            print(f"  - Payment Method: {payment_req.payment_method}")
            print(f"  - Amount: ${payment_req.amount:.2f}")
            print(f"  - Total Amount: ${payment_req.total_amount:.2f}")
            print(f"  - Customer Email: {payment_req.customer_email}")
            print(f"  - Status: {payment_req.status}")
            print(f"  - Approval Status: {getattr(payment_req, 'approval_status', 'N/A')}")
            
        except frappe.DoesNotExistError:
            print(f"✗ Payment Request '{payment_request_name}' not found")
            
            # Look for any Manual Payment requests
            manual_payments = frappe.get_all(
                "Payment Request",
                filters={"is_manual_payment": 1},
                fields=["name", "title", "customer_email", "payment_method", "amount", "status"],
                limit=5
            )
            
            if manual_payments:
                print(f"\nFound {len(manual_payments)} manual payment requests:")
                for mp in manual_payments:
                    print(f"  - {mp.name}: {mp.title} (${mp.amount}, {mp.status})")
                
                # Use the first one for testing
                payment_req = frappe.get_doc("Payment Request", manual_payments[0].name)
                print(f"\nUsing '{payment_req.name}' for testing instead...")
            else:
                print("No manual payment requests found. Creating a test one...")
                
                # Create a test payment request
                payment_req = frappe.get_doc({
                    "doctype": "Payment Request",
                    "title": payment_request_name,
                    "payment_method": "Bank Transfer",
                    "cart_id": "CART-0046",
                    "amount": 500.00,
                    "fees": 0,
                    "total_amount": 500.00,
                    "customer_email": "test@example.com",
                    "customer_name": "Test Customer",
                    "status": "Pending",
                    "created_by": "Administrator",
                    "is_manual_payment": 1,
                    "approval_status": "Pending Approval"
                })
                payment_req.insert(ignore_permissions=True)
                frappe.db.commit()
                print(f"✓ Created test Payment Request: {payment_req.name}")
        
        print(f"\n2. Testing Email Queue Before Sending")
        
        # Check current email queue count
        queue_count_before = frappe.db.count("Email Queue")
        print(f"Email Queue count before: {queue_count_before}")
        
        print(f"\n3. Testing send_payment_request_notification_email function")
        
        # Import the email function
        from rockettradeline.api.payment import send_payment_request_notification_email
        
        # Test the notification email function
        try:
            result = send_payment_request_notification_email(payment_req)
            print(f"✓ Email function returned: {result}")
        except Exception as e:
            print(f"✗ Error in send_payment_request_notification_email: {str(e)}")
            import traceback
            traceback.print_exc()
        
        print(f"\n4. Checking Email Queue After Sending")
        
        # Check email queue count after
        queue_count_after = frappe.db.count("Email Queue")
        print(f"Email Queue count after: {queue_count_after}")
        print(f"New emails added: {queue_count_after - queue_count_before}")
        
        # Get recent email queue entries
        recent_emails = frappe.get_all(
            "Email Queue",
            fields=["name", "status", "creation"],
            order_by="creation desc",
            limit=3
        )
        
        if recent_emails:
            print(f"\nRecent Email Queue entries:")
            for email in recent_emails:
                # Get full document to access recipients
                full_email = frappe.get_doc("Email Queue", email.name)
                recipients = [r.recipient for r in full_email.recipients] if full_email.recipients else ["No recipients"]
                print(f"  - {email.name}: Status {email.status} → Recipients: {recipients}")
                
                # Check for errors
                if full_email.error:
                    print(f"    Error: {full_email.error}")
        
        print(f"\n5. Testing send_payment_approval_email function")
        
        # Import and test approval email function
        from rockettradeline.api.payment import send_payment_approval_email
        
        # Set some required fields for approval email
        payment_req.approved_at = frappe.utils.now_datetime()
        payment_req.transaction_id = "TEST_TRANSACTION_123"
        
        try:
            result = send_payment_approval_email(payment_req)
            print(f"✓ Approval email function returned: {result}")
        except Exception as e:
            print(f"✗ Error in send_payment_approval_email: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Check email queue again
        queue_count_final = frappe.db.count("Email Queue")
        print(f"\nFinal Email Queue count: {queue_count_final}")
        print(f"Total new emails added: {queue_count_final - queue_count_before}")
        
        print(f"\n6. Testing Email Configuration")
        
        # Check email settings
        email_settings = frappe.get_single("Email Account")
        print(f"Email Account configured: {bool(email_settings)}")
        
        # Check if there's an outgoing email account
        outgoing_accounts = frappe.get_all(
            "Email Account",
            filters={"enable_outgoing": 1},
            fields=["name", "email_id", "smtp_server", "enable_outgoing"]
        )
        
        if outgoing_accounts:
            print(f"Outgoing email accounts found: {len(outgoing_accounts)}")
            for account in outgoing_accounts:
                print(f"  - {account.name}: {account.email_id} via {account.smtp_server}")
        else:
            print("✗ No outgoing email accounts configured!")
        
        print(f"\n7. Testing Direct frappe.sendmail")
        
        # Test direct sendmail
        try:
            frappe.sendmail(
                recipients=["test@example.com"],
                subject="Direct Test Email",
                message="This is a direct test email from the test script.",
                delayed=False
            )
            print("✓ Direct frappe.sendmail executed without error")
        except Exception as e:
            print(f"✗ Error in direct frappe.sendmail: {str(e)}")
        
        # Final email queue check
        final_queue_count = frappe.db.count("Email Queue")
        print(f"\nFinal Email Queue count after direct test: {final_queue_count}")
        
        # Get the latest email queue entries
        latest_emails = frappe.get_all(
            "Email Queue",
            fields=["name", "status", "recipient", "subject", "creation", "error"],
            order_by="creation desc",
            limit=5
        )
        
        if latest_emails:
            print(f"\nLatest Email Queue entries:")
            for email in latest_emails:
                error_info = f" (Error: {email.error})" if email.error else ""
                print(f"  - {email.name}: {email.subject} → {email.recipient} ({email.status}){error_info}")
        
        print(f"\n=== Test Complete ===")
        
    except Exception as e:
        print(f"Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        frappe.destroy()

if __name__ == "__main__":
    test_payment_email_notifications()

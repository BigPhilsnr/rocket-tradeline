import frappe

def debug_sendmail_behavior():
    """Debug frappe.sendmail behavior to understand the issue"""
    try:
        print("=== Debugging frappe.sendmail behavior ===")
        
        queue_before = frappe.db.count("Email Queue")
        print(f"Email queue count before: {queue_before}")
        
        # Test 1: Simple sendmail call
        print("\n1. Testing simple sendmail call:")
        try:
            result = frappe.sendmail(
                recipients=["info@rockettradeline.com"],
                subject="Debug Test Email",
                message="<p>This is a debug test email.</p>",
                delayed=False
            )
            print(f"  sendmail result: {result}")
            print(f"  sendmail type: {type(result)}")
        except Exception as e:
            print(f"  sendmail exception: {str(e)}")
            print(f"  exception type: {type(e)}")
        
        queue_after = frappe.db.count("Email Queue")
        print(f"Email queue count after: {queue_after}")
        print(f"Emails added: {queue_after - queue_before}")
        
        # Check the latest email status
        if queue_after > queue_before:
            latest_email = frappe.get_all(
                "Email Queue",
                fields=["name", "status", "error"],
                order_by="creation desc",
                limit=1
            )[0]
            
            print(f"\nLatest email details:")
            print(f"  Name: {latest_email.name}")
            print(f"  Status: {latest_email.status}")
            print(f"  Error: {latest_email.get('error', 'None')}")
            
            # Get full document
            full_email = frappe.get_doc("Email Queue", latest_email.name)
            if full_email.error:
                print(f"  Full error: {full_email.error}")
        
        # Test 2: Check if delayed=True makes a difference
        print(f"\n2. Testing with delayed=True:")
        queue_before = queue_after
        
        try:
            result = frappe.sendmail(
                recipients=["info@rockettradeline.com"],
                subject="Debug Test Email - Delayed",
                message="<p>This is a delayed debug test email.</p>",
                delayed=True
            )
            print(f"  sendmail result (delayed): {result}")
        except Exception as e:
            print(f"  sendmail exception (delayed): {str(e)}")
        
        queue_after = frappe.db.count("Email Queue")
        print(f"Email queue count after delayed: {queue_after}")
        print(f"Emails added: {queue_after - queue_before}")
        
        return True
        
    except Exception as e:
        print(f"Debug test failed: {str(e)}")
        frappe.log_error(f"Debug sendmail error: {str(e)}", "Debug Sendmail Error")
        return False

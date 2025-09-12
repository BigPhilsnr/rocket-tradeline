import frappe

def check_email_queue_structure():
    """Check Email Queue doctype structure"""
    try:
        # Get Email Queue doctype meta
        meta = frappe.get_meta("Email Queue")
        print(f"Email Queue fields:")
        for field in meta.fields:
            print(f"  - {field.fieldname}: {field.fieldtype}")
        
        # Try to get recent emails with different field names
        print("\nTrying different field approaches:")
        
        # Method 1: Get all fields
        try:
            recent_emails = frappe.get_all("Email Queue", 
                                         order_by="creation desc",
                                         limit=3)
            print(f"✓ Method 1 - Basic get_all: Found {len(recent_emails)} emails")
            if recent_emails:
                print(f"  Latest email: {recent_emails[0]}")
        except Exception as e:
            print(f"✗ Method 1 failed: {str(e)}")
        
        # Method 2: Get specific fields
        try:
            recent_emails = frappe.get_all("Email Queue", 
                                         fields=["name", "creation", "status", "sender", "recipients"],
                                         order_by="creation desc",
                                         limit=3)
            print(f"✓ Method 2 - With fields: Found {len(recent_emails)} emails")
            if recent_emails:
                print(f"  Latest email: {recent_emails[0]}")
        except Exception as e:
            print(f"✗ Method 2 failed: {str(e)}")
            
        # Method 3: Check for recipient vs recipients
        try:
            recent_emails = frappe.get_all("Email Queue", 
                                         fields=["name", "creation", "status", "recipients"],
                                         order_by="creation desc",
                                         limit=1)
            print(f"✓ Method 3 - recipients field works: Found {len(recent_emails)} emails")
        except Exception as e:
            print(f"✗ Method 3 failed: {str(e)}")
            
    except Exception as e:
        print(f"Error checking Email Queue: {str(e)}")

def test_simple_email_send():
    """Test a simple email send"""
    try:
        print("\n=== Testing Simple Email Send ===")
        
        # Get queue count before
        before_count = frappe.db.count("Email Queue")
        print(f"Email Queue count before: {before_count}")
        
        # Send a simple test email
        result = frappe.sendmail(
            recipients=["test@example.com"],
            subject="Test Email - Payment Debug",
            message="<p>This is a test email to debug payment notifications.</p>",
            delayed=False
        )
        
        print(f"Send email result: {result}")
        
        # Get queue count after
        after_count = frappe.db.count("Email Queue")
        print(f"Email Queue count after: {after_count}")
        print(f"New emails added: {after_count - before_count}")
        
        return True
        
    except Exception as e:
        print(f"Error in simple email test: {str(e)}")
        frappe.log_error(f"Simple email test error: {str(e)}", "Email Test Error")
        return False

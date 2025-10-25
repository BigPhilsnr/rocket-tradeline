#!/usr/bin/env python3
"""
Debug Email Account Configuration
Check what fields are available and fix the always_bcc issue
"""

import frappe

def execute():
    """Debug email account configuration"""
    try:
        print("=== Debugging Email Account Configuration ===")
        
        # Get all email accounts
        email_accounts = frappe.get_all("Email Account",
            filters={"enable_outgoing": 1},
            fields=["name", "email_id", "enable_outgoing", "default_outgoing"]
        )
        
        print(f"Found {len(email_accounts)} outgoing email accounts:")
        for account in email_accounts:
            print(f"  - {account.name}: {account.email_id} (Default: {account.default_outgoing})")
        
        if email_accounts:
            # Get the full document for the first account
            account_name = email_accounts[0].name
            account_doc = frappe.get_doc("Email Account", account_name)
            
            print(f"\n=== Full Email Account Details: {account_name} ===")
            
            # Check if always_bcc field exists
            has_always_bcc = hasattr(account_doc, 'always_bcc')
            print(f"Has 'always_bcc' field: {has_always_bcc}")
            
            if has_always_bcc:
                print(f"always_bcc value: {account_doc.always_bcc}")
            
            # Check other common BCC fields
            bcc_fields = ['bcc', 'default_bcc', 'always_use_bcc', 'auto_bcc']
            print("\nOther BCC-related fields:")
            for field in bcc_fields:
                if hasattr(account_doc, field):
                    value = getattr(account_doc, field, None)
                    print(f"  - {field}: {value}")
            
            # Get all available fields
            print(f"\nAll available fields in Email Account:")
            meta = frappe.get_meta("Email Account")
            for field in meta.fields:
                if field.fieldtype not in ['Section Break', 'Column Break', 'HTML']:
                    print(f"  - {field.fieldname} ({field.fieldtype})")
        
        # Test frappe.sendmail with minimal parameters to avoid the always_bcc issue
        print(f"\n=== Testing frappe.sendmail with minimal parameters ===")
        try:
            frappe.sendmail(
                recipients=["siranjofuw@gmail.com"],
                subject="Test Email - Minimal Parameters",
                message="<p>This is a test email with minimal parameters to avoid the always_bcc issue.</p>",
                now=True
            )
            print("✅ Minimal frappe.sendmail test successful!")
        except Exception as e:
            print(f"❌ Minimal frappe.sendmail failed: {str(e)}")
        
        return {
            "success": True,
            "email_accounts": email_accounts,
            "has_always_bcc": has_always_bcc if 'has_always_bcc' in locals() else False
        }
        
    except Exception as e:
        error_msg = f"Email account debug failed: {str(e)}"
        print(f"❌ {error_msg}")
        frappe.log_error(error_msg)
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    execute()
#!/usr/bin/env python3
"""
Fix Email Account always_bcc Issue
Update the email account to set the always_bcc field properly
"""

import frappe

def execute():
    """Fix the always_bcc field issue"""
    try:
        print("=== Fixing Email Account always_bcc Issue ===")
        
        # Get the email account
        email_accounts = frappe.get_all("Email Account",
            filters={"enable_outgoing": 1, "default_outgoing": 1},
            fields=["name"]
        )
        
        if not email_accounts:
            print("❌ No default outgoing email account found")
            return {"success": False, "error": "No email account found"}
        
        account_name = email_accounts[0].name
        print(f"Fixing email account: {account_name}")
        
        # Get the account document
        account_doc = frappe.get_doc("Email Account", account_name)
        
        # Set always_bcc to empty string if it doesn't exist or is None
        try:
            current_bcc = getattr(account_doc, 'always_bcc', None)
            print(f"Current always_bcc value: {current_bcc}")
        except:
            print("always_bcc field not accessible, will set it directly")
        
        # Set the field directly in the database
        frappe.db.set_value("Email Account", account_name, "always_bcc", "")
        frappe.db.commit()
        
        print("✅ Set always_bcc to empty string in database")
        
        # Reload the document
        account_doc.reload()
        
        # Test access to always_bcc
        try:
            bcc_value = account_doc.always_bcc
            print(f"✅ always_bcc field now accessible: '{bcc_value}'")
        except Exception as e:
            print(f"❌ still can't access always_bcc: {str(e)}")
        
        # Test sending an email again
        print(f"\n=== Testing frappe.sendmail after fix ===")
        try:
            frappe.sendmail(
                recipients=["siranjofuw@gmail.com"],
                subject="Test Email - After Fix",
                message="<p>This is a test email after fixing the always_bcc issue.</p>",
                now=True
            )
            print("✅ frappe.sendmail test successful after fix!")
            return {"success": True, "message": "Email account fixed and test email sent"}
        except Exception as e:
            print(f"❌ frappe.sendmail still failed: {str(e)}")
            
            # Try alternative approach - update all fields
            print("Trying alternative fix...")
            try:
                # Set all potentially problematic fields
                update_fields = {
                    "always_bcc": "",
                    "signature": account_doc.signature or "",
                    "footer": account_doc.footer or ""
                }
                
                for field, value in update_fields.items():
                    frappe.db.set_value("Email Account", account_name, field, value)
                
                frappe.db.commit()
                print("✅ Updated all email account fields")
                
                # Test again
                frappe.sendmail(
                    recipients=["siranjofuw@gmail.com"],
                    subject="Test Email - Alternative Fix",
                    message="<p>This is a test email after alternative fix.</p>",
                    now=True
                )
                print("✅ frappe.sendmail successful with alternative fix!")
                return {"success": True, "message": "Alternative fix successful"}
                
            except Exception as e2:
                print(f"❌ Alternative fix also failed: {str(e2)}")
                return {"success": False, "error": str(e2)}
        
    except Exception as e:
        error_msg = f"Fix failed: {str(e)}"
        print(f"❌ {error_msg}")
        frappe.log_error(error_msg)
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    execute()
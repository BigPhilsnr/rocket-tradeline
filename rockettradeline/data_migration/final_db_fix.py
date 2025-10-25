#!/usr/bin/env python3
"""
Final Database Schema Fix
Add the missing always_bcc column properly
"""

import frappe

def execute():
    """Add the missing always_bcc column with correct method"""
    try:
        print("=== Final Database Schema Fix ===")
        
        # Get the current database name
        db_name = frappe.conf.db_name
        print(f"Database name: {db_name}")
        
        # Check if always_bcc column exists
        try:
            has_column = frappe.db.sql("""
                SELECT COUNT(*) as count 
                FROM information_schema.COLUMNS 
                WHERE TABLE_NAME = 'tabEmail Account' 
                AND COLUMN_NAME = 'always_bcc' 
                AND TABLE_SCHEMA = %s
            """, (db_name,))
            
            column_exists = has_column[0][0] > 0
            print(f"always_bcc column exists: {column_exists}")
            
            if not column_exists:
                print("Adding always_bcc column...")
                frappe.db.sql("""
                    ALTER TABLE `tabEmail Account` 
                    ADD COLUMN `always_bcc` TEXT NULL
                """)
                
                # Set default value for existing records
                frappe.db.sql("UPDATE `tabEmail Account` SET `always_bcc` = ''")
                frappe.db.commit()
                print("✅ Added always_bcc column and set default values")
            else:
                print("always_bcc column already exists")
            
        except Exception as e:
            print(f"Error with always_bcc column: {str(e)}")
        
        # Also check for other potentially missing fields that might cause issues
        required_fields = {
            'sent_folder_name': 'TEXT',
            'backend_app_flow': 'INT(1) DEFAULT 0'
        }
        
        for field_name, field_type in required_fields.items():
            try:
                has_field = frappe.db.sql("""
                    SELECT COUNT(*) as count 
                    FROM information_schema.COLUMNS 
                    WHERE TABLE_NAME = 'tabEmail Account' 
                    AND COLUMN_NAME = %s 
                    AND TABLE_SCHEMA = %s
                """, (field_name, db_name))
                
                field_exists = has_field[0][0] > 0
                print(f"{field_name} column exists: {field_exists}")
                
                if not field_exists:
                    print(f"Adding {field_name} column...")
                    frappe.db.sql(f"""
                        ALTER TABLE `tabEmail Account` 
                        ADD COLUMN `{field_name}` {field_type}
                    """)
                    frappe.db.commit()
                    print(f"✅ Added {field_name} column")
                    
            except Exception as e:
                print(f"Error with {field_name} field: {str(e)}")
        
        # Clear any cached Email Account documents
        frappe.clear_cache(doctype="Email Account")
        
        # Test frappe.sendmail now
        print(f"\n=== Testing frappe.sendmail after final fix ===")
        try:
            frappe.sendmail(
                recipients=["siranjofuw@gmail.com"],
                subject="Test Email - Final Database Fix",
                message="<p>This is a test email after the final database schema fix.</p>",
                now=True
            )
            print("✅ frappe.sendmail successful after final fix!")
            return {"success": True, "message": "Database fixed and email sent successfully"}
            
        except Exception as e:
            print(f"❌ frappe.sendmail still failed: {str(e)}")
            
            # Let's try bypassing frappe.sendmail and use the Email Template Custom directly
            print("Trying Email Template Custom system...")
            try:
                from rockettradeline.rockettradeline.doctype.email_template_custom.email_template_custom import send_email_template
                
                send_email_template(
                    template_name="Email Verification",
                    recipients=["siranjofuw@gmail.com"],
                    parameters={
                        "full_name": "Test User",
                        "site_name": "rockettradeline.com",
                        "verification_link": "https://test.com"
                    }
                )
                print("✅ Email Template Custom system works!")
                return {"success": True, "message": "Email Template Custom system successful"}
                
            except Exception as e2:
                print(f"❌ Email Template Custom also failed: {str(e2)}")
                return {"success": False, "error": str(e2)}
        
    except Exception as e:
        error_msg = f"Final fix failed: {str(e)}"
        print(f"❌ {error_msg}")
        frappe.log_error(error_msg)
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    execute()
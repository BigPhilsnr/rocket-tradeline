#!/usr/bin/env python3
"""
Manual Database Schema Fix
Add the missing always_bcc column to the tabEmail Account table
"""

import frappe

def execute():
    """Manually add the missing always_bcc column"""
    try:
        print("=== Manual Database Schema Fix ===")
        
        # Check current table structure
        print("Checking current Email Account table structure...")
        try:
            result = frappe.db.sql("DESCRIBE `tabEmail Account`")
            print("Current columns:")
            for row in result:
                print(f"  - {row[0]} ({row[1]})")
        except Exception as e:
            print(f"Error describing table: {str(e)}")
        
        # Check if always_bcc column exists
        try:
            has_column = frappe.db.sql("""
                SELECT COUNT(*) as count 
                FROM information_schema.COLUMNS 
                WHERE TABLE_NAME = 'tabEmail Account' 
                AND COLUMN_NAME = 'always_bcc' 
                AND TABLE_SCHEMA = %s
            """, (frappe.db.get_db_name(),))
            
            column_exists = has_column[0][0] > 0
            print(f"always_bcc column exists: {column_exists}")
            
            if not column_exists:
                print("Adding always_bcc column...")
                frappe.db.sql("""
                    ALTER TABLE `tabEmail Account` 
                    ADD COLUMN `always_bcc` TEXT NULL
                """)
                print("✅ Added always_bcc column")
                
                # Set default value
                frappe.db.sql("UPDATE `tabEmail Account` SET `always_bcc` = '' WHERE `always_bcc` IS NULL")
                frappe.db.commit()
                print("✅ Set default values for always_bcc")
            
        except Exception as e:
            print(f"Error adding column: {str(e)}")
        
        # Test frappe.sendmail now
        print(f"\n=== Testing frappe.sendmail after manual fix ===")
        try:
            frappe.sendmail(
                recipients=["siranjofuw@gmail.com"],
                subject="Test Email - Manual Database Fix",
                message="<p>This is a test email after manually fixing the database schema.</p>",
                now=True
            )
            print("✅ frappe.sendmail successful after manual database fix!")
            return {"success": True, "message": "Database manually fixed and email sent"}
        except Exception as e:
            print(f"❌ frappe.sendmail still failed: {str(e)}")
            
            # Try with a more complete email structure
            try:
                print("Trying with complete email structure...")
                frappe.sendmail(
                    recipients=["siranjofuw@gmail.com"],
                    subject="Test Email - Complete Structure",
                    message="<p>This is a test email with complete structure.</p>",
                    sender="info@rockettradeline.com",
                    now=True,
                    attachments=None,
                    reply_to=None
                )
                print("✅ Complete structure email successful!")
                return {"success": True, "message": "Email sent with complete structure"}
            except Exception as e2:
                print(f"❌ Complete structure also failed: {str(e2)}")
                return {"success": False, "error": str(e2)}
        
    except Exception as e:
        error_msg = f"Manual fix failed: {str(e)}"
        print(f"❌ {error_msg}")
        frappe.log_error(error_msg)
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    execute()
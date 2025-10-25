#!/usr/bin/env python3
"""
Check and Re-transfer Allowed File Name Records
"""

import frappe
from rockettradeline.data_migration.transfer_doctype import transfer_doctype

def check_current_records():
    """Check what Allowed File Name records currently exist"""
    try:
        records = frappe.get_all("Allowed File Name",
            fields=["name", "file_name", "description", "category", "is_active", "creation"],
            order_by="creation desc"
        )
        
        print(f"Found {len(records)} Allowed File Name records:")
        for record in records:
            print(f"  - {record.name}: {record.file_name} ({record.category}) - Active: {record.is_active}")
        
        return records
    except Exception as e:
        print(f"Error checking current records: {str(e)}")
        return []

def clear_existing_records():
    """Clear existing Allowed File Name records to avoid duplicates"""
    try:
        existing_records = frappe.get_all("Allowed File Name", fields=["name"])
        
        if existing_records:
            print(f"Clearing {len(existing_records)} existing records...")
            for record in existing_records:
                frappe.delete_doc("Allowed File Name", record.name, ignore_permissions=True)
            
            frappe.db.commit()
            print("Existing records cleared successfully")
        else:
            print("No existing records to clear")
            
    except Exception as e:
        print(f"Error clearing existing records: {str(e)}")
        frappe.db.rollback()

def execute():
    """Main execution function"""
    try:
        print("=== Checking Current Allowed File Name Records ===")
        current_records = check_current_records()
        
        print(f"\n=== Current record count: {len(current_records)} ===")
        
        # Ask if we should clear and re-transfer
        print("\n=== Clearing existing records and re-transferring ===")
        clear_existing_records()
        
        print("\n=== Starting fresh transfer from remote database ===")
        result = transfer_doctype("Allowed File Name")
        
        print("\n=== Transfer completed - checking new records ===")
        new_records = check_current_records()
        
        print(f"\n=== Transfer Summary ===")
        print(f"Records transferred: {len(new_records)}")
        
        if result:
            print(f"Transfer result: {result}")
        
        return {
            "success": True,
            "records_transferred": len(new_records),
            "details": new_records
        }
        
    except Exception as e:
        error_msg = f"Failed to check/transfer Allowed File Name records: {str(e)}"
        print(error_msg)
        frappe.log_error(error_msg)
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    execute()
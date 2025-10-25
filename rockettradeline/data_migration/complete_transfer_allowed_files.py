#!/usr/bin/env python3
"""
Complete Transfer of All Allowed File Name Records
Fetches all 17 records from remote database
"""

import frappe
import pymysql
from datetime import datetime
from frappe.utils import now, get_datetime

def get_external_connection():
    """Establish connection to external database"""
    try:
        connection = pymysql.connect(
            host='142.132.165.13',
            port=3306,
            user='external_user',
            password='SecurePassword123!',
            database='_9ee58f4274d12503',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        frappe.log_error(f"Failed to connect to external database: {str(e)}")
        raise

def fetch_all_allowed_file_names():
    """Fetch all Allowed File Name records from remote database"""
    try:
        connection = get_external_connection()
        
        with connection.cursor() as cursor:
            # Get all records from remote database
            query = """
            SELECT 
                name, owner, creation, modified, modified_by, docstatus, idx,
                file_name, description, is_active, category, created_date, modified_date
            FROM `tabAllowed File Name`
            ORDER BY creation ASC
            """
            
            cursor.execute(query)
            records = cursor.fetchall()
            
        connection.close()
        
        print(f"✅ Fetched {len(records)} records from remote database")
        return records
        
    except Exception as e:
        error_msg = f"Failed to fetch records from remote database: {str(e)}"
        print(f"❌ {error_msg}")
        frappe.log_error(error_msg)
        return []

def insert_allowed_file_name_record(record):
    """Insert a single Allowed File Name record"""
    try:
        # Check if record already exists
        if frappe.db.exists("Allowed File Name", record.get('name')):
            print(f"⚠️  Record {record.get('name')} already exists, skipping...")
            return False
        
        # Create new document
        doc = frappe.new_doc("Allowed File Name")
        
        # Set all field values
        doc.name = record.get('name')
        doc.file_name = record.get('file_name')
        doc.description = record.get('description')
        doc.is_active = record.get('is_active', 1)
        doc.category = record.get('category')
        doc.created_date = record.get('created_date')
        doc.modified_date = record.get('modified_date')
        
        # Set standard fields
        doc.owner = record.get('owner', 'Administrator')
        doc.creation = record.get('creation', now())
        doc.modified = record.get('modified', now())
        doc.modified_by = record.get('modified_by', 'Administrator')
        doc.docstatus = record.get('docstatus', 0)
        doc.idx = record.get('idx', 0)
        
        # Insert without validations
        doc.flags.ignore_permissions = True
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_validate = True
        doc.insert(ignore_if_duplicate=True)
        
        print(f"✅ Inserted: {record.get('name')} - {record.get('file_name')}")
        return True
        
    except Exception as e:
        error_msg = f"Failed to insert record {record.get('name')}: {str(e)}"
        print(f"❌ {error_msg}")
        frappe.log_error(error_msg)
        return False

def execute():
    """Main execution function"""
    try:
        print("=== Starting Complete Allowed File Name Transfer ===")
        
        # Fetch all records from remote database
        remote_records = fetch_all_allowed_file_names()
        
        if not remote_records:
            print("❌ No records found in remote database")
            return {"success": False, "error": "No remote records found"}
        
        print(f"\n=== Found {len(remote_records)} records in remote database ===")
        
        # Insert each record
        inserted_count = 0
        skipped_count = 0
        failed_count = 0
        
        for record in remote_records:
            try:
                result = insert_allowed_file_name_record(record)
                if result:
                    inserted_count += 1
                else:
                    skipped_count += 1
            except Exception as e:
                failed_count += 1
                print(f"❌ Failed to process record {record.get('name')}: {str(e)}")
        
        # Commit all changes
        frappe.db.commit()
        
        # Get final count from local database
        final_records = frappe.get_all("Allowed File Name", fields=["name", "file_name", "category"])
        
        print(f"\n=== Transfer Summary ===")
        print(f"Remote records found: {len(remote_records)}")
        print(f"Records inserted: {inserted_count}")
        print(f"Records skipped (already exist): {skipped_count}")
        print(f"Records failed: {failed_count}")
        print(f"Final local count: {len(final_records)}")
        
        print(f"\n=== Final Local Records ===")
        for record in final_records:
            print(f"  - {record.name}: {record.file_name} ({record.category})")
        
        return {
            "success": True,
            "remote_count": len(remote_records),
            "inserted": inserted_count,
            "skipped": skipped_count,
            "failed": failed_count,
            "final_local_count": len(final_records),
            "local_records": final_records
        }
        
    except Exception as e:
        error_msg = f"Transfer failed: {str(e)}"
        print(f"❌ {error_msg}")
        frappe.log_error(error_msg)
        frappe.db.rollback()
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    execute()
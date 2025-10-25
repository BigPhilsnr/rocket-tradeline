#!/usr/bin/env python3
"""
Debug Remote Database Connection and Data
"""

import frappe
import pymysql
from rockettradeline.data_migration.transfer_doctype import get_external_connection

def test_connection_and_fetch_data():
    """Test connection and fetch data from remote database"""
    try:
        print("=== Testing Remote Database Connection ===")
        
        # Get connection
        connection = get_external_connection()
        print("✅ Connection established successfully")
        
        with connection.cursor() as cursor:
            # Test basic connection
            cursor.execute("SELECT CONNECTION_ID(), USER(), VERSION(), DATABASE()")
            conn_info = cursor.fetchone()
            print(f"Connection Info: {conn_info}")
            
            # Check if the table exists
            table_name = "tabAllowedFileName"
            cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
            table_exists = cursor.fetchone()
            
            if not table_exists:
                # Try alternative table name
                table_name = "tabAllowed File Name"
                cursor.execute(f"SHOW TABLES LIKE %s", (table_name,))
                table_exists = cursor.fetchone()
            
            if table_exists:
                print(f"✅ Found table: {table_name}")
                
                # Get table structure
                cursor.execute(f"DESCRIBE `{table_name}`")
                columns = cursor.fetchall()
                print("Table structure:")
                for col in columns:
                    print(f"  - {col}")
                
                # Count records
                cursor.execute(f"SELECT COUNT(*) as count FROM `{table_name}`")
                count_result = cursor.fetchone()
                print(f"Total records in remote table: {count_result['count']}")
                
                # Fetch sample records
                cursor.execute(f"SELECT * FROM `{table_name}` LIMIT 10")
                records = cursor.fetchall()
                print(f"Sample records (first 10):")
                for i, record in enumerate(records):
                    print(f"  Record {i+1}: {record}")
                
                return {
                    "success": True,
                    "table_name": table_name,
                    "total_records": count_result['count'],
                    "sample_records": records
                }
                
            else:
                # List all tables to see what's available
                cursor.execute("SHOW TABLES")
                all_tables = cursor.fetchall()
                print("❌ Allowed File Name table not found")
                print("Available tables:")
                for table in all_tables:
                    if 'allowed' in str(table).lower() or 'file' in str(table).lower():
                        print(f"  - {table}")
                
                return {
                    "success": False,
                    "error": "Table not found",
                    "available_tables": all_tables
                }
        
        connection.close()
        
    except Exception as e:
        error_msg = f"Error testing remote database: {str(e)}"
        print(f"❌ {error_msg}")
        frappe.log_error(error_msg)
        return {
            "success": False,
            "error": str(e)
        }

def execute():
    """Main execution function"""
    return test_connection_and_fetch_data()

if __name__ == "__main__":
    execute()
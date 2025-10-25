#!/usr/bin/env python3
"""
Data Transfer Script for Frappe
Transfers entire doctype data from external database to current site

Usage:
    bench --site rockettradeline.com execute rockettradeline.data_migration.transfer_doctype.transfer_doctype --args "Role Profile"
"""

import frappe
import pymysql
import json
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


def get_doctype_fields(doctype):
    """Get all fields for a doctype"""
    meta = frappe.get_meta(doctype)
    fields = []
    
    # Add standard fields
    standard_fields = ['name', 'owner', 'creation', 'modified', 'modified_by', 'docstatus', 'idx']
    for field in standard_fields:
        fields.append(field)
    
    # Add doctype specific fields
    for df in meta.fields:
        if df.fieldtype not in ['Section Break', 'Column Break', 'HTML', 'Heading']:
            fields.append(df.fieldname)
    
    return fields


def get_child_tables(doctype):
    """Get all child table doctypes for a given parent doctype"""
    meta = frappe.get_meta(doctype)
    child_tables = []
    
    for df in meta.fields:
        if df.fieldtype == 'Table':
            child_tables.append(df.options)
    
    return child_tables


def fetch_external_data(connection, doctype, fields):
    """Fetch all records from external database for given doctype"""
    try:
        with connection.cursor() as cursor:
            # Convert doctype to table name (keep spaces as they are, add 'tab' prefix)
            table_name = f"tab{doctype}"
            
            # Build field list for SELECT query
            field_list = ', '.join([f"`{field}`" for field in fields])
            
            query = f"SELECT {field_list} FROM `{table_name}`"
            cursor.execute(query)
            records = cursor.fetchall()
            
            frappe.log_error(f"Fetched {len(records)} records from {table_name}")
            return records
            
    except Exception as e:
        frappe.log_error(f"Failed to fetch data from {doctype}: {str(e)}")
        return []


def insert_record(doctype, record_data, fields):
    """Insert a single record into current site database"""
    try:
        # Check if record already exists
        if frappe.db.exists(doctype, record_data.get('name')):
            frappe.log_error(f"Record {record_data.get('name')} already exists in {doctype}")
            return False
        
        # Create new document
        doc = frappe.new_doc(doctype)
        
        # Set field values
        for field in fields:
            if field in record_data and record_data[field] is not None:
                value = record_data[field]
                
                # Handle datetime fields
                if isinstance(value, str) and field in ['creation', 'modified']:
                    try:
                        value = get_datetime(value)
                    except:
                        value = now()
                
                # Handle JSON fields
                elif isinstance(value, str) and value.startswith('{'):
                    try:
                        value = json.loads(value)
                    except:
                        pass
                
                setattr(doc, field, value)
        
        # Insert without validations to avoid conflicts
        doc.flags.ignore_permissions = True
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_validate = True
        doc.insert(ignore_if_duplicate=True)
        
        frappe.db.commit()
        return True
        
    except Exception as e:
        frappe.log_error(f"Failed to insert record {record_data.get('name')} in {doctype}: {str(e)}")
        frappe.db.rollback()
        return False


def transfer_child_table_data(connection, parent_doctype, child_doctype, parent_records):
    """Transfer child table data for all parent records"""
    try:
        # Get child table fields
        child_fields = get_doctype_fields(child_doctype)
        child_fields.append('parent')  # Add parent field
        child_fields.append('parenttype')  # Add parenttype field
        child_fields.append('parentfield')  # Add parentfield field
        
        # Fetch child records from external database
        child_records = fetch_external_data(connection, child_doctype, child_fields)
        
        inserted_count = 0
        for child_record in child_records:
            # Only process child records that belong to transferred parent records
            parent_name = child_record.get('parent')
            if parent_name and any(pr.get('name') == parent_name for pr in parent_records):
                if insert_record(child_doctype, child_record, child_fields):
                    inserted_count += 1
        
        frappe.log_error(f"Transferred {inserted_count} child records for {child_doctype}")
        return inserted_count
        
    except Exception as e:
        frappe.log_error(f"Failed to transfer child table data for {child_doctype}: {str(e)}")
        return 0


def transfer_doctype(doctype_name):
    """
    Main function to transfer entire doctype data from external database
    
    Args:
        doctype_name (str): Name of the doctype to transfer
    """
    try:
        frappe.log_error(f"Starting transfer for doctype: {doctype_name}")
        
        # Validate doctype exists
        if not frappe.db.exists("DocType", doctype_name):
            frappe.throw(f"DocType '{doctype_name}' does not exist")
        
        # Get connection to external database
        connection = get_external_connection()
        
        # Get doctype fields
        fields = get_doctype_fields(doctype_name)
        
        # Fetch data from external database
        external_records = fetch_external_data(connection, doctype_name, fields)
        
        if not external_records:
            frappe.msgprint(f"No records found for {doctype_name} in external database")
            return
        
        # Transfer main doctype records
        inserted_count = 0
        for record in external_records:
            if insert_record(doctype_name, record, fields):
                inserted_count += 1
        
        frappe.log_error(f"Transferred {inserted_count} main records for {doctype_name}")
        
        # Transfer child table data
        child_tables = get_child_tables(doctype_name)
        child_counts = {}
        
        for child_doctype in child_tables:
            child_count = transfer_child_table_data(connection, doctype_name, child_doctype, external_records)
            child_counts[child_doctype] = child_count
        
        # Close connection
        connection.close()
        
        # Summary message
        message = f"""
        Data Transfer Complete for {doctype_name}:
        - Main records transferred: {inserted_count}/{len(external_records)}
        """
        
        if child_counts:
            message += "\n- Child table records transferred:"
            for child_doctype, count in child_counts.items():
                message += f"\n  • {child_doctype}: {count}"
        
        frappe.msgprint(message)
        frappe.log_error(f"Transfer completed successfully for {doctype_name}")
        
        return {
            'doctype': doctype_name,
            'main_records': inserted_count,
            'total_external': len(external_records),
            'child_tables': child_counts
        }
        
    except Exception as e:
        error_msg = f"Transfer failed for {doctype_name}: {str(e)}"
        frappe.log_error(error_msg)
        frappe.throw(error_msg)


def transfer_multiple_doctypes(doctype_list):
    """
    Transfer multiple doctypes in sequence
    
    Args:
        doctype_list (list): List of doctype names to transfer
    """
    results = []
    
    for doctype_name in doctype_list:
        try:
            result = transfer_doctype(doctype_name)
            results.append(result)
        except Exception as e:
            frappe.log_error(f"Failed to transfer {doctype_name}: {str(e)}")
            results.append({
                'doctype': doctype_name,
                'error': str(e)
            })
    
    return results


def list_databases():
    """List available databases on external server"""
    try:
        connection = get_external_connection()
        with connection.cursor() as cursor:
            cursor.execute("SHOW DATABASES")
            databases = cursor.fetchall()
            frappe.msgprint(f"Available databases: {databases}")
            return databases
        connection.close()
    except Exception as e:
        frappe.throw(f"Failed to list databases: {str(e)}")
        return []


def select_database(database_name):
    """Select and use a specific database"""
    try:
        connection = get_external_connection()
        with connection.cursor() as cursor:
            cursor.execute(f"USE `{database_name}`")
            cursor.execute("SELECT DATABASE()")
            result = cursor.fetchone()
            frappe.msgprint(f"Selected database: {result}")
        connection.close()
        return True
    except Exception as e:
        frappe.throw(f"Failed to select database {database_name}: {str(e)}")
        return False


def test_connection():
    """Test connection to external database"""
    try:
        connection = get_external_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT CONNECTION_ID(), USER(), VERSION()")
            result = cursor.fetchone()
            frappe.msgprint(f"Connected to external server: {result}")
        connection.close()
        return True
    except Exception as e:
        frappe.throw(f"Connection test failed: {str(e)}")
        return False


if __name__ == "__main__":
    # Example usage
    import sys
    if len(sys.argv) > 1:
        doctype = sys.argv[1]
        transfer_doctype(doctype)
    else:
        print("Usage: python transfer_doctype.py 'DocType Name'")
#!/usr/bin/env python3
"""
Utility to explore external database structure
"""

import frappe
import pymysql


def get_external_connection():
    """Establish connection to external database"""
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


def list_external_tables():
    """List all tables in external database"""
    try:
        connection = get_external_connection()
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            table_names = [list(table.values())[0] for table in tables]
            
            # Filter for Role Profile related tables
            role_tables = [t for t in table_names if 'role' in t.lower()]
            
            print(f"Total tables: {len(table_names)}")
            print(f"Role-related tables: {role_tables}")
            
            frappe.msgprint(f"Found {len(table_names)} tables. Role-related: {role_tables}")
            
        connection.close()
        return table_names
        
    except Exception as e:
        frappe.throw(f"Failed to list tables: {str(e)}")


def check_role_profile_data():
    """Check if Role Profile table exists and show sample data"""
    try:
        connection = get_external_connection()
        with connection.cursor() as cursor:
            # Try different possible table names
            possible_names = ['tabRole Profile', 'tabRoleProfile', 'tabRole_Profile', 'tabrole_profile']
            
            for table_name in possible_names:
                try:
                    cursor.execute(f"SELECT COUNT(*) as count FROM `{table_name}`")
                    count = cursor.fetchone()
                    
                    cursor.execute(f"SELECT * FROM `{table_name}` LIMIT 5")
                    sample_data = cursor.fetchall()
                    
                    print(f"Table {table_name} has {count['count']} records")
                    print(f"Sample data: {sample_data}")
                    
                    frappe.msgprint(f"Found table {table_name} with {count['count']} records")
                    return sample_data
                    
                except pymysql.err.ProgrammingError:
                    print(f"Table {table_name} does not exist")
                    continue
                    
        connection.close()
        frappe.msgprint("No Role Profile table found")
        
    except Exception as e:
        frappe.throw(f"Failed to check Role Profile data: {str(e)}")


def explore_doctype_table():
    """Check DocType table to see what doctypes are available"""
    try:
        connection = get_external_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM tabDocType WHERE name LIKE '%Role%' OR name LIKE '%role%'")
            doctypes = cursor.fetchall()
            
            print(f"Role-related doctypes: {doctypes}")
            frappe.msgprint(f"Role-related doctypes found: {[d['name'] for d in doctypes]}")
            
        connection.close()
        return doctypes
        
    except Exception as e:
        frappe.throw(f"Failed to explore doctypes: {str(e)}")
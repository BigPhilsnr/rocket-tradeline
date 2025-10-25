#!/usr/bin/env python3
"""
Simple wrapper functions for data transfer
"""

import frappe
from rockettradeline.data_migration.transfer_doctype import (
    transfer_doctype, 
    transfer_multiple_doctypes, 
    test_connection, 
    list_databases,
    select_database
)


def migrate_role_profiles():
    """Transfer Role Profile doctype from external database"""
    return transfer_doctype("Role Profile")


def migrate_common_doctypes():
    """Transfer commonly needed doctypes"""
    doctypes_to_transfer = [
        "Role Profile",
        "User",
        "Email Domain", 
        "Role Permission",
        "Custom Field",
        "Property Setter"
    ]
    return transfer_multiple_doctypes(doctypes_to_transfer)


def test_external_db():
    """Test external database connection"""
    return test_connection()


def list_external_databases():
    """List available databases on external server"""
    return list_databases()


def use_external_database(db_name):
    """Select a specific database on external server"""
    return select_database(db_name)


# Frappe whitelist functions for API access
@frappe.whitelist()
def api_transfer_doctype(doctype_name):
    """API endpoint to transfer a specific doctype"""
    if frappe.session.user != "Administrator":
        frappe.throw("Only Administrator can perform data transfers")
    
    return transfer_doctype(doctype_name)


@frappe.whitelist() 
def api_test_connection():
    """API endpoint to test external database connection"""
    if frappe.session.user != "Administrator":
        frappe.throw("Only Administrator can test database connections")
    
    return test_connection()
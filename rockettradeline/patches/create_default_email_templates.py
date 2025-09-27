# Copyright (c) 2025, RocketTradeline and contributors
# Patch to create default email templates

import frappe


def execute():
    """Create default email templates"""
    try:
        print("Starting default email template creation...")
        
        # Check if DocTypes exist first
        if not frappe.db.exists("DocType", "Email Template Custom"):
            print("Email Template Custom DocType not found, skipping template creation")
            return
            
        if not frappe.db.exists("DocType", "Email Template Parameter"):
            print("Email Template Parameter DocType not found, skipping template creation")
            return
        
        # Import and create templates
        from rockettradeline.utils.email_templates import create_default_templates
        
        created_templates = create_default_templates()
        
        if created_templates:
            print(f"Successfully created default email templates: {', '.join(created_templates)}")
        else:
            print("All default email templates already exist or none were created")
            
    except ImportError as e:
        print(f"Import error - skipping email template creation: {str(e)}")
    except Exception as e:
        error_msg = f"Error creating default email templates: {str(e)}"
        print(error_msg)
        # Don't use frappe.log_error here as it might cause cascading issues
        # frappe.log_error(error_msg, "Email Template Patch")
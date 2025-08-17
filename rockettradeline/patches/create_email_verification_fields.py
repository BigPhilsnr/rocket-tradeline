import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    """Create custom fields for email verification in User doctype"""
    
    # Check if fields already exist
    if frappe.db.exists("Custom Field", {"fieldname": "email_verified", "dt": "User"}):
        return
    
    custom_fields = {
        "User": [
            {
                "fieldname": "email_verification_section",
                "label": "Email Verification",
                "fieldtype": "Section Break",
                "insert_after": "enabled",
                "collapsible": 1
            },
            {
                "fieldname": "email_verified",
                "label": "Email Verified",
                "fieldtype": "Check",
                "default": 0,
                "read_only": 1,
                "insert_after": "email_verification_section"
            },
            {
                "fieldname": "email_verification_token",
                "label": "Email Verification Token",
                "fieldtype": "Data",
                "hidden": 1,
                "read_only": 1,
                "insert_after": "email_verified"
            },
            {
                "fieldname": "email_verification_sent_at",
                "label": "Email Verification Sent At",
                "fieldtype": "Datetime",
                "hidden": 1,
                "read_only": 1,
                "insert_after": "email_verification_token"
            },
            {
                "fieldname": "email_verified_at",
                "label": "Email Verified At",
                "fieldtype": "Datetime",
                "hidden": 1,
                "read_only": 1,
                "insert_after": "email_verification_sent_at"
            }
        ]
    }
    
    create_custom_fields(custom_fields)
    frappe.db.commit()
    
    print("Email verification custom fields created successfully!")

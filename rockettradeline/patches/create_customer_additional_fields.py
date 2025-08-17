import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    """Add custom fields to Customer doctype for enhanced profile management"""
    
    # Custom fields to add to Customer doctype
    # Note: gender and tax_id already exist in Customer doctype
    custom_fields = [
        {
            "doctype": "Custom Field",
            "dt": "Customer",
            "fieldname": "date_of_birth",
            "label": "Date of Birth",
            "fieldtype": "Date",
            "insert_after": "gender",
            "in_list_view": 0,
            "in_standard_filter": 0
        }
    ]
    
    for field_data in custom_fields:
        # Check if field already exists
        if not frappe.db.exists("Custom Field", {"dt": field_data["dt"], "fieldname": field_data["fieldname"]}):
            custom_field = frappe.get_doc(field_data)
            custom_field.insert()
            print(f"Created custom field: {field_data['fieldname']} for {field_data['dt']}")
        else:
            print(f"Custom field {field_data['fieldname']} already exists for {field_data['dt']}")
    
    frappe.db.commit()
    print("Customer additional fields setup completed")

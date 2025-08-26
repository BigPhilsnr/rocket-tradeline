import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    """Add custom flags to Customer doctype for RocketTradeline app"""
    
    # Custom fields to add to Customer doctype
    custom_fields = {
        "Customer": [
            {
                "fieldname": "is_seller",
                "label": "Is Seller",
                "fieldtype": "Check",
                "default": "0",
                "insert_after": "customer_type",
                "description": "Check if this customer is also a seller",
                "in_list_view": 1,
                "in_standard_filter": 1,
                "allow_on_submit": 1
            },
            {
                "fieldname": "has_signed_agreement",
                "label": "Has Signed Agreement",
                "fieldtype": "Check",
                "default": "0",
                "insert_after": "is_seller",
                "description": "Check if customer has signed the required agreement",
                "in_list_view": 1,
                "in_standard_filter": 1,
                "allow_on_submit": 1
            },
            {
                "fieldname": "is_questionnaire_filled",
                "label": "Is Questionnaire Filled",
                "fieldtype": "Check",
                "default": "0",
                "insert_after": "has_signed_agreement",
                "description": "Check if customer has filled the required questionnaire",
                "in_list_view": 1,
                "in_standard_filter": 1,
                "allow_on_submit": 1
            },
            {
                "fieldname": "section_break_customer_flags",
                "label": "Customer Status",
                "fieldtype": "Section Break",
                "insert_after": "customer_type",
                "collapsible": 0
            },
            {
                "fieldname": "column_break_customer_flags",
                "fieldtype": "Column Break",
                "insert_after": "has_signed_agreement"
            },
            {
                "fieldname": "agreement_signed_date",
                "label": "Agreement Signed Date",
                "fieldtype": "Datetime",
                "insert_after": "is_questionnaire_filled",
                "depends_on": "has_signed_agreement",
                "description": "Date and time when agreement was signed"
            },
            {
                "fieldname": "questionnaire_filled_date",
                "label": "Questionnaire Filled Date",
                "fieldtype": "Datetime",
                "insert_after": "agreement_signed_date",
                "depends_on": "is_questionnaire_filled",
                "description": "Date and time when questionnaire was filled"
            }
        ]
    }
    
    # Create custom fields
    create_custom_fields(custom_fields)
    
    # Also update any existing customer records to ensure flags are properly set
    frappe.db.sql("""
        UPDATE `tabCustomer` 
        SET 
            is_seller = COALESCE(is_seller, 0),
            has_signed_agreement = COALESCE(has_signed_agreement, 0),
            is_questionnaire_filled = COALESCE(is_questionnaire_filled, 0)
        WHERE 
            is_seller IS NULL OR 
            has_signed_agreement IS NULL OR 
            is_questionnaire_filled IS NULL
    """)
    
    frappe.db.commit()
    print("Customer flags setup completed successfully")
    print("Added fields: is_seller, has_signed_agreement, is_questionnaire_filled")
    print("Added tracking fields: agreement_signed_date, questionnaire_filled_date")

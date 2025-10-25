#!/usr/bin/env python3
"""
Update Cardholder Removal Required Email Template
Simplifies the template to use a clean, concise format
"""

import frappe
from frappe import _

def update_cardholder_removal_template():
    """Update the Cardholder Removal Required template with simplified content"""
    
    template_name = "Cardholder Removal Required"
    
    # Check if template exists
    if frappe.db.exists("Email Template Custom", template_name):
        doc = frappe.get_doc("Email Template Custom", template_name)
        print(f"Updating existing template: {template_name}")
    else:
        doc = frappe.new_doc("Email Template Custom")
        doc.template_name = template_name
        print(f"Creating new template: {template_name}")
    
    # Update template fields
    doc.subject = "Cardholder Removal Required - Tradeline Term Expired"
    doc.description = "Notification to cardholder to remove expired authorized user from tradeline"
    doc.template_type = "Notification"
    
    # Simple, clean HTML content matching the user's format
    doc.html_content = """
        <p style="color: #374151; font-size: 16px; margin: 0 0 10px 0;">Dear Rocket Tradeline Cardholder,</p>
        
        <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0 0 20px 0;">
            We hope this message finds you well.
        </p>
        
        <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0 0 25px 0;">
            We are writing to inform you that the 60-day term for the authorized user added to your tradeline has officially expired. 
            At this time, you may proceed with removing the authorized user from the account associated with the tradeline listed below:
        </p>
        
        <div style="background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px; padding: 20px; margin-bottom: 25px;">
            <p style="margin: 5px 0; color: #374151; font-size: 15px;"><strong>Tradeline:</strong> {{bank_name}} {{age_year}} Year ${{credit_limit}}</p>
            <p style="margin: 5px 0; color: #374151; font-size: 15px;"><strong>Authorized User:</strong> {{customer_name}}</p>
        </div>
        
        <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0 0 20px 0;">
            Please ensure that the authorized user is removed immediately, and kindly destroy any physical card issued in their name to prevent any potential misuse.
        </p>
        
        <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0 0 25px 0;">
            If you require assistance with the removal process or have any questions, feel free to contact us.
        </p>
        
        <p style="color: #374151; font-size: 16px; margin: 25px 0 0 0;">
            Thank you for your continued partnership.
        </p>
    """
    
    # Clear existing parameters
    doc.parameters = []
    
    # Add simplified parameters (only what's needed for the template)
    parameters = [
        {"parameter_name": "cardholder_name", "parameter_label": "Cardholder Name", "parameter_type": "Data", "is_required": 0},
        {"parameter_name": "customer_name", "parameter_label": "Customer Name (AU)", "parameter_type": "Data", "is_required": 1},
        {"parameter_name": "bank_name", "parameter_label": "Bank Name", "parameter_type": "Data", "is_required": 1},
        {"parameter_name": "age_year", "parameter_label": "Age Year", "parameter_type": "Int", "is_required": 1},
        {"parameter_name": "credit_limit", "parameter_label": "Credit Limit", "parameter_type": "Float", "is_required": 1}
    ]
    
    for param in parameters:
        doc.append("parameters", param)
    
    # Disable version tracking to avoid creating unnecessary version entries
    doc.flags.ignore_version = True
    
    # Save the template
    doc.save()
    frappe.db.commit()
    
    print(f"✅ Successfully updated '{template_name}'")
    print("\nThe template now uses a simple, clean format with:")
    print("  - Greeting and introduction")
    print("  - Clear expiry notification")
    print("  - Tradeline details (Bank, Year, Credit Limit)")
    print("  - Authorized User name")
    print("  - Removal instructions")
    print("  - Card destruction reminder")
    print("  - Contact information")
    print("  - Thank you message")
    
    return {"success": True, "template": template_name}

if __name__ == "__main__":
    frappe.init(site="rockettradeline.com")
    frappe.connect()
    update_cardholder_removal_template()
    frappe.destroy()

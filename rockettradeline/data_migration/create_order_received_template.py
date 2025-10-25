#!/usr/bin/env python3
"""
Create Email Template for Order Received Notification
"""

import frappe

def execute():
    """Create the Tradeline Order Received email template"""
    try:
        print("=== Creating Tradeline Order Received Email Template ===")
        
        # Check if template already exists
        existing_template = frappe.db.exists("Email Template Custom", "Tradeline Order Received")
        if existing_template:
            print("✅ Template already exists, updating...")
            template = frappe.get_doc("Email Template Custom", existing_template)
        else:
            print("Creating new template...")
            template = frappe.new_doc("Email Template Custom")
            template.name = "Tradeline Order Received"
        
        # Set template fields
        template.template_name = "Tradeline Order Received"
        template.subject = "Tradeline Order Received {{ customer_name }}"
        template.enabled = 1
        template.template_type = "System"
        template.description = "Notification sent when tradeline order is received - sent to account manager or customer"
        
        template.content = """
<h3 style="color: #374151; margin: 0 0 20px 0;">📋 Tradeline Order Received - {{ customer_name }}</h3>
<p style="color: #374151; font-size: 16px; margin: 0 0 10px 0;">Hello {{ recipient_name.split()[0] if recipient_name else "Team" }},</p>

<p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0 0 25px 0;">
    Thank you for submitting the Tradeline Order Form. We've received your request and are beginning the processing steps. Here's what to expect next:
</p>

<div style="background-color: #f0f9ff; border-left: 4px solid #17B26A; padding: 20px; border-radius: 6px; margin: 25px 0;">
    <h4 style="color: #374151; margin: 0 0 15px 0; font-size: 16px;">✅ Verification Call (Within 24 Hours)</h4>
    <p style="margin: 0; color: #6b7280; line-height: 1.6;">
        A quick call will be completed with the authorized user (AU) to verify their identity, relationship, and consent.
    </p>
</div>

<div style="background-color: #f0f9ff; border-left: 4px solid #17B26A; padding: 20px; border-radius: 6px; margin: 25px 0;">
    <h4 style="color: #374151; margin: 0 0 15px 0; font-size: 16px;">✅ AU Agreement (If Not Already on File)</h4>
    <p style="margin: 0; color: #6b7280; line-height: 1.6;">
        If we don't already have a signed AU agreement, a link will be provided for the AU to review and complete before processing continues.
    </p>
</div>

<div style="background-color: #f0f9ff; border-left: 4px solid #17B26A; padding: 20px; border-radius: 6px; margin: 25px 0;">
    <h4 style="color: #374151; margin: 0 0 15px 0; font-size: 16px;">✅ AU Confirmation (Within 24–48 Hours)</h4>
    <p style="margin: 0; color: #6b7280; line-height: 1.6;">
        You'll receive a confirmation email once the authorized user (AU) has been successfully added to the tradeline.
    </p>
</div>

<div style="background-color: #f0f9ff; border-left: 4px solid #17B26A; padding: 20px; border-radius: 6px; margin: 25px 0;">
    <h4 style="color: #374151; margin: 0 0 15px 0; font-size: 16px;">✅ Update the AU's Address</h4>
    <p style="margin: 0; color: #6b7280; line-height: 1.6;">
        After receiving confirmation, follow the instructions in the email to update the AU's address on their credit profile. Tools like SmartCredit or IdentityIQ can be helpful for this step.
    </p>
</div>

<div style="background-color: #f0f9ff; border-left: 4px solid #17B26A; padding: 20px; border-radius: 6px; margin: 25px 0;">
    <h4 style="color: #374151; margin: 0 0 15px 0; font-size: 16px;">✅ Reporting Timeline & Reminder</h4>
    <p style="margin: 0; color: #6b7280; line-height: 1.6;">
        We'll send you a reminder around the tradeline's statement closing date to check whether it has posted. Please note that it may take up to two full billing cycles for the tradeline to appear on the AU's credit report.
    </p>
</div>

<p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 25px 0 0 0;">
    If you have any questions in the meantime, feel free to reach out.
</p>
"""
        
        # Save the template
        if existing_template:
            template.save()
            print("✅ Updated existing template")
        else:
            template.insert()
            print("✅ Created new template")
        
        print(f"Template Name: {template.template_name}")
        print(f"Subject: {template.subject}")
        print(f"Status: {'Enabled' if template.enabled else 'Disabled'}")
        
        return {"success": True, "template_name": template.template_name}
        
    except Exception as e:
        error_msg = f"Failed to create email template: {str(e)}"
        print(f"❌ {error_msg}")
        frappe.log_error(error_msg)
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    execute()
#!/usr/bin/env python3
"""
Script to create the Tradeline Expiry Reminder email template
"""
import frappe

def create_expiry_reminder_template():
    """Create the Tradeline Expiry Reminder template"""
    
    template_name = "Tradeline Expiry Reminder"
    
    # HTML content matching the user's requested format
    html_content = """
                <div style="margin-bottom: 25px;">
                    <p style="color: #374151; font-size: 16px; margin: 0 0 10px 0;">Hello,</p>
                    <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0 0 25px 0;">
                        This is a friendly reminder that the 60-day term (+30 day free extension) for the authorized user (AU) spot on the tradeline below has now ended, and the AU will be removed.
                    </p>
                </div>
                
                <div style="background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin: 25px 0;">
                    {{tradelines_html}}
                </div>
                
                <div style="background-color: #f0f9ff; border-left: 4px solid #17B26A; padding: 20px; border-radius: 6px; margin: 25px 0;">
                    <p style="margin: 0 0 15px 0; color: #374151; line-height: 1.6;">
                        If you wish to extend the AU spot, you can resubmit a new tradeline order at your earliest convenience to maintain credit activity and continue benefiting from the tradeline.
                    </p>
                </div>
                
                <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 25px 0 0 0;">
                    We appreciate your business and look forward to continuing to support you on your credit-building journey. If you have any questions or need assistance placing a new order, feel free to reply to this email.
                </p>
            """
    
    subject = "Tradeline Term Expiring Soon"
    description = "Notification sent 7 days before tradeline expiry to remind client"
    
    try:
        # Check if template already exists
        if frappe.db.exists("Email Template Custom", template_name):
            print(f"Template '{template_name}' already exists, updating...")
            
            # Update existing template
            template_doc = frappe.get_doc("Email Template Custom", template_name)
            template_doc.subject = subject
            template_doc.description = description
            template_doc.html_content = html_content
            template_doc.template_type = "Notification"
            template_doc.is_active = 1
            
            # Clear and update parameters
            template_doc.parameters = []
            template_doc.append("parameters", {
                "parameter_name": "customer_name",
                "parameter_label": "Customer Name",
                "parameter_type": "Data",
                "is_required": 1
            })
            template_doc.append("parameters", {
                "parameter_name": "tradelines_html",
                "parameter_label": "Tradelines HTML",
                "parameter_type": "Text",
                "is_required": 1
            })
            template_doc.append("parameters", {
                "parameter_name": "client_email",
                "parameter_label": "Client Email",
                "parameter_type": "Data",
                "is_required": 1
            })
            
            template_doc.flags.ignore_version = True
            template_doc.save(ignore_permissions=True)
            print(f"✅ Successfully updated '{template_name}'")
            
        else:
            print(f"Creating new template: {template_name}")
            
            # Create new template
            template_doc = frappe.get_doc({
                "doctype": "Email Template Custom",
                "template_name": template_name,
                "subject": subject,
                "description": description,
                "template_type": "Notification",
                "html_content": html_content,
                "is_active": 1
            })
            
            template_doc.append("parameters", {
                "parameter_name": "customer_name",
                "parameter_label": "Customer Name",
                "parameter_type": "Data",
                "is_required": 1
            })
            template_doc.append("parameters", {
                "parameter_name": "tradelines_html",
                "parameter_label": "Tradelines HTML",
                "parameter_type": "Text",
                "is_required": 1
            })
            template_doc.append("parameters", {
                "parameter_name": "client_email",
                "parameter_label": "Client Email",
                "parameter_type": "Data",
                "is_required": 1
            })
            
            template_doc.insert(ignore_permissions=True)
            print(f"✅ Successfully created '{template_name}'")
        
        frappe.db.commit()
        
        print("\nThe template uses a simple div-based layout with:")
        print("  - Customer greeting")
        print("  - Expiry reminder message")
        print("  - Tradeline details (AU name, tradeline name, expiry date)")
        print("  - Renewal call-to-action")
        print("  - Support message")
        
        return {"success": True, "template": template_name}
        
    except Exception as e:
        error_msg = f"❌ Error creating/updating template: {str(e)}"
        print(error_msg)
        frappe.log_error(error_msg, "Template Creation Error")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    frappe.init(site="rockettradeline.com")
    frappe.connect()
    result = create_expiry_reminder_template()
    frappe.destroy()

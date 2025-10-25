#!/usr/bin/env python3
"""
Script to update only the Tradeline Closing Date Notification template
"""
import frappe

def update_closing_date_notification_template():
    """Update only the Tradeline Closing Date Notification template with fixed HTML"""
    
    template_name = "Tradeline Closing Date Notification"
    
    # Simplified HTML content using div-based layout instead of tables
    html_content = """
                <div style="margin-bottom: 25px;">
                    <h3 style="color: #374151; margin: 0 0 20px 0;">📅 Tradeline Closing Date Reached</h3>
                    <p style="color: #374151; font-size: 16px; margin: 0 0 10px 0;">Hello,</p>
                    <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0 0 25px 0;">
                        I'm writing to let you know that we've reached the close date for your Tradeline(s).
                    </p>
                </div>
                
                <div style="background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin: 25px 0;">
                    <h4 style="color: #374151; margin: 0 0 15px 0; font-size: 16px;">Your Tradeline Details:</h4>
                    {{tradelines_html}}
                </div>
                
                <div style="background-color: #f0f9ff; border-left: 4px solid #17B26A; padding: 20px; border-radius: 6px; margin: 25px 0;">
                    <h4 style="color: #374151; margin: 0 0 15px 0; font-size: 16px;">📊 Next Steps - Check Your Credit Report</h4>
                    <p style="margin: 0 0 15px 0; color: #6b7280; line-height: 1.6;">
                        Please take a moment to check your credit report(s) to see if the Tradeline has posted. If you don't see it yet, no worries - it can sometimes take a few extra days or up to two full billing cycles for the credit bureaus to reflect the update.
                    </p>
                </div>
                
                <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 20px; border-radius: 6px; margin: 25px 0;">
                    <h4 style="color: #92400e; margin: 0 0 15px 0; font-size: 16px;">⏰ Important Timing Information</h4>
                    <ul style="margin: 0; padding-left: 20px; color: #92400e; line-height: 1.6;">
                        <li style="margin: 8px 0;">You will remain on a tradeline for a minimum of two billing cycles, up to 60 days total</li>
                        <li style="margin: 8px 0;">At the end of the term, you will be removed from the tradeline</li>
                        <li style="margin: 8px 0;">Your credit score may adjust accordingly after removal</li>
                        <li style="margin: 8px 0;"><strong>If you plan to apply for loans or credit cards, do so before the term ends</strong></li>
                    </ul>
                </div>
                
                <div style="background-color: #f9fafb; border-left: 4px solid #6b7280; padding: 15px; border-radius: 6px; margin: 25px 0;">
                    <p style="margin: 0 0 10px 0; color: #374151; font-weight: 600;">
                        💡 Want More Tradelines?
                    </p>
                    <p style="margin: 0; color: #6b7280; line-height: 1.6; font-size: 14px;">
                        If you'd like to purchase additional tradelines or extend the current term, please submit a new Tradeline Order. Let me know if you have any questions—I'm here to help!
                    </p>
                </div>
                
                <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 25px 0 0 0;">
                    If you have any questions or concerns, please don't hesitate to reach out. We're here to support your credit journey!
                </p>
            """
    
    try:
        if not frappe.db.exists("Email Template Custom", template_name):
            print(f"❌ Template '{template_name}' does not exist!")
            return {"success": False, "error": "Template not found"}
        
        # Get the template
        template_doc = frappe.get_doc("Email Template Custom", template_name)
        
        print(f"Updating '{template_name}' template with fixed HTML structure...")
        
        # Update only the HTML content
        template_doc.html_content = html_content
        
        # Save the template
        template_doc.save(ignore_permissions=True)
        frappe.db.commit()
        
        print(f"✅ Successfully updated '{template_name}'")
        print("\nThe template now has the {{tradelines_table}} placeholder inside the <tbody> tags")
        print("This will ensure the table rows are properly inserted when the email is sent.")
        
        return {"success": True, "template": template_name}
        
    except Exception as e:
        error_msg = f"❌ Error updating template: {str(e)}"
        print(error_msg)
        frappe.log_error(error_msg, "Template Update Error")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    frappe.init(site="rockettradeline.com")
    frappe.connect()
    result = update_closing_date_notification_template()
    frappe.destroy()

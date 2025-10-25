#!/usr/bin/env python3
"""
Update Home Workspace with API Doctypes
Adds links to all doctypes used in the API files
"""

import frappe

def update_home_workspace():
    """Update the Home workspace with links to API doctypes"""
    
    # Doctype categories and descriptions
    doctype_links = [
        # Core Business Doctypes
        ("Client Tradelines", "Manage client tradeline orders and assignments"),
        ("Tradeline", "View and manage tradeline inventory"),
        ("Tradeline Bank", "Manage banks and their tradeline offerings"),
        ("Tradeline Cart", "View shopping carts and cart management"),
        ("Customer", "Manage clients, sellers, and cardholders"),
        
        # Payment & Financial
        ("Payment Request", "Track payment requests and transactions"),
        ("Payment Configuration", "Configure payment methods and settings"),
        ("Payment Verification", "Review and verify manual payments"),
        ("Mode of Payment", "Manage available payment methods"),
        
        # Communication & Content
        ("Email Template Custom", "Manage custom email templates"),
        ("Email Account", "Configure email accounts for sending"),
        ("Email Group", "Manage email marketing groups"),
        ("Email Group Member", "View email group subscribers"),
        ("Site Content", "Manage website content sections"),
        ("Page Content", "Edit page-specific content"),
        ("FAQ", "Manage frequently asked questions"),
        ("Testimonial", "Customer testimonials and reviews"),
        
        # Feedback & Notifications
        ("Tradeline Feedback", "View customer feedback submissions"),
        ("Notification Log", "System notification history"),
        ("Notification Settings", "User notification preferences"),
        
        # Files & Documents
        ("File", "Manage uploaded files and attachments"),
        ("Allowed File Name", "Configure allowed file naming patterns"),
        
        # User Management
        ("User", "Manage system users and permissions"),
        ("Role Profile", "Define user role profiles"),
        ("Customer Type", "Customer classification types"),
        ("Customer Group", "Group customers for management"),
        ("Territory", "Geographic territories for customers"),
        
        # Address Management
        ("Address", "Manage customer and cardholder addresses"),
        ("Contact", "Manage contact information"),
    ]
    
    try:
        # Get the Home workspace
        if not frappe.db.exists("Workspace", "Home"):
            print("Home workspace does not exist")
            return {"success": False, "message": "Home workspace not found"}
        
        workspace = frappe.get_doc("Workspace", "Home")
        
        # Clear existing links
        workspace.links = []
        
        # Add a card break to separate sections
        workspace.append("links", {
            "type": "Card Break",
            "label": "API Doctypes"
        })
        
        # Add doctype links
        for doctype_name, description in doctype_links:
            # Check if doctype exists
            if frappe.db.exists("DocType", doctype_name):
                workspace.append("links", {
                    "type": "Link",
                    "link_type": "DocType",
                    "link_to": doctype_name,
                    "label": doctype_name,
                    "description": description,
                    "hidden": 0,
                    "only_for": None,
                    "is_query_report": 0
                })
                print(f"Added link for: {doctype_name}")
            else:
                print(f"Skipped (not found): {doctype_name}")
        
        # Save the workspace
        workspace.flags.ignore_version = True
        workspace.flags.ignore_permissions = True
        workspace.save()
        frappe.db.commit()
        
        print(f"\n✅ Successfully updated Home workspace with {len(doctype_links)} doctype links")
        
        return {
            "success": True,
            "message": f"Updated Home workspace with {len(doctype_links)} links",
            "total_links": len(doctype_links)
        }
        
    except Exception as e:
        error_msg = f"Failed to update Home workspace: {str(e)}"
        frappe.log_error(error_msg, "Update Home Workspace Error")
        print(f"\n❌ Error: {error_msg}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    frappe.init(site="rockettradeline.com")
    frappe.connect()
    update_home_workspace()
    frappe.destroy()

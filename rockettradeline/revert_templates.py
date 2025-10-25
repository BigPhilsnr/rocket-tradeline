#!/usr/bin/env python3
"""
Script to revert Email Template Custom documents to their versions before 14:51:55
"""
import frappe
from frappe.utils import get_datetime
from datetime import datetime

def revert_templates():
    """Revert templates that were updated at 14:51:55 back to their versions BEFORE that time"""
    
    # Mapping of templates to their specific version IDs from BEFORE the 14:51:55 update
    templates_to_revert = {
        'Email Verification': 'ee6p0b0p3t',  # 2025-09-28 13:38:50
        'Order Shipped': 'vjs184npif',  # 2025-10-09 14:06:01
        'Account Setup Required': 'ro9oaqer2s',  # 2025-10-09 09:26:21
        'Refund Request Notification': 'ps6217c2ja',  # 2025-10-04 08:19:35
        'Payment Approval': '4q03js9rqq',  # 2025-10-09 11:31:02
        'AU Assignment Notification': '7jbpr5sutl',  # 2025-10-11 13:39:32
        'Payment Request Notification': '6udmufsd9g',  # 2025-10-11 05:26:54
        'Active Status Notification': 'jbe3j1p4tf',  # 2025-10-11 13:59:35
    }
    
    reverted = []
    errors = []
    no_versions = []
    
    for template_name, version_id in templates_to_revert.items():
        try:
            # Check if template exists
            if not frappe.db.exists("Email Template Custom", template_name):
                print(f"⚠️  Template '{template_name}' does not exist, skipping...")
                continue
            
            # Check if version exists
            if not frappe.db.exists("Version", version_id):
                print(f"⚠️  Version '{version_id}' for '{template_name}' not found, skipping...")
                no_versions.append(template_name)
                continue
            
            # Get the version document
            version_doc = frappe.get_doc("Version", version_id)
            
            print(f"Reverting '{template_name}' to version {version_id} from {version_doc.creation}...")
            
            # Parse the data
            import json
            version_data = json.loads(version_doc.data)
            
            # Get current template
            template_doc = frappe.get_doc("Email Template Custom", template_name)
            
            # Revert the fields
            if "html_content" in version_data:
                template_doc.html_content = version_data["html_content"]
            if "subject" in version_data:
                template_doc.subject = version_data["subject"]
            if "description" in version_data:
                template_doc.description = version_data["description"]
            if "template_type" in version_data:
                template_doc.template_type = version_data["template_type"]
            
            # Revert parameters if they exist
            if "parameters" in version_data and version_data["parameters"]:
                template_doc.parameters = []
                for param in version_data["parameters"]:
                    template_doc.append("parameters", param)
            
            # Save the reverted template
            template_doc.flags.ignore_version = True  # Don't create another version for this revert
            template_doc.save(ignore_permissions=True)
            frappe.db.commit()
            
            print(f"✅ Successfully reverted '{template_name}' to version from {version_doc.creation}")
            reverted.append(template_name)
            
        except Exception as e:
            error_msg = f"❌ Error reverting '{template_name}': {str(e)}"
            print(error_msg)
            import traceback
            print(traceback.format_exc())
            errors.append({"template": template_name, "error": str(e)})
    
    # Handle templates that had no previous versions (newly created at 14:51:55)
    new_templates = ['Password Reset', 'Payment Confirmation', 'Welcome Email', 'Payment Failed', 
                     'Cardholder Removal Required', 'Client Tradeline Expiration']
    
    print("\n" + "="*60)
    print("REVERT SUMMARY")
    print("="*60)
    print(f"✅ Successfully reverted: {len(reverted)} templates")
    if reverted:
        for t in reverted:
            print(f"   - {t}")
    
    if no_versions:
        print(f"\n⚠️  Templates with no previous version: {len(no_versions)}")
        for t in no_versions:
            print(f"   - {t}")
    
    print(f"\nℹ️  Templates that were newly created (no revert needed): {len(new_templates)}")
    for t in new_templates:
        print(f"   - {t}")
    
    if errors:
        print(f"\n❌ Errors: {len(errors)}")
        for err in errors:
            print(f"   - {err['template']}: {err['error']}")
    
    return {"reverted": reverted, "no_versions": no_versions, "new_templates": new_templates, "errors": errors}

if __name__ == "__main__":
    frappe.init(site="rockettradeline.com")
    frappe.connect()
    result = revert_templates()
    frappe.destroy()

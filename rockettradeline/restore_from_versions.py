#!/usr/bin/env python3
"""
Script to apply the version data from the 14:51:55 versions
These versions contain the state BEFORE the generator update
"""
import frappe
import json

def apply_version_data():
    """Apply the exact version data from the specified versions"""
    
    # Map of templates to their version IDs from 14:51:55 (these contain the BEFORE state)
    version_mapping = {
        'Email Verification': 'i0e34go58u',
        'Password Reset': 'i0f63fmuv1',
        'Payment Confirmation': 'i0fe53vcf9',
        'Welcome Email': 'i0f00gtg0d',
        'Order Shipped': 'i0fh180qs6',
        'Account Setup Required': 'i0gqfjt05i',
        'Payment Failed': 'i0g9uo98on',
        'Cardholder Removal Required': 'i0g0sbqhga',
        'Client Tradeline Expiration': 'i0g2d0dt8u',
        'Refund Request Notification': 'i0hasekeir',
        'Payment Approval': 'i0hbo6er32',
        'AU Assignment Notification': 'i0hv0b2qaf',
        'Payment Request Notification': 'i0hog4r8kq',
        'Active Status Notification': 'i0i4nig2bn',
    }
    
    restored = []
    errors = []
    
    for template_name, version_id in version_mapping.items():
        try:
            # Check if version exists
            if not frappe.db.exists("Version", version_id):
                print(f"⚠️  Version '{version_id}' not found for '{template_name}', skipping...")
                continue
            
            # Get the version document
            version_doc = frappe.get_doc("Version", version_id)
            version_data = json.loads(version_doc.data)
            
            print(f"Restoring '{template_name}' from version {version_id} ({version_doc.creation})...")
            
            # Check if template exists
            if not frappe.db.exists("Email Template Custom", template_name):
                print(f"⚠️  Template '{template_name}' does not exist, skipping...")
                continue
            
            # Get current template
            template_doc = frappe.get_doc("Email Template Custom", template_name)
            
            # The version data contains "changed" which has the fields that were there BEFORE the change
            # We need to look at the "changed" array to get the original values
            if "changed" in version_data:
                for change in version_data["changed"]:
                    field_name = change[0]
                    old_value = change[1]  # The original value before the change
                    new_value = change[2]  # The new value after the change
                    
                    # We want the OLD value (before the generator ran)
                    if hasattr(template_doc, field_name):
                        setattr(template_doc, field_name, old_value)
                        print(f"  - Restored field '{field_name}'")
            
            # Handle removed parameters (these were present before the change)
            if "removed" in version_data:
                # These parameters were removed, so we need to add them back
                for removal in version_data["removed"]:
                    if removal[0] == "parameters":
                        param_data = removal[1]
                        # Check if parameter already exists
                        exists = False
                        for existing_param in template_doc.parameters:
                            if existing_param.parameter_name == param_data.get("parameter_name"):
                                exists = True
                                break
                        
                        if not exists:
                            template_doc.append("parameters", {
                                "parameter_name": param_data.get("parameter_name"),
                                "parameter_label": param_data.get("parameter_label"),
                                "parameter_type": param_data.get("parameter_type"),
                                "is_required": param_data.get("is_required", 0),
                                "default_value": param_data.get("default_value"),
                                "description": param_data.get("description")
                            })
                            print(f"  - Restored parameter '{param_data.get('parameter_name')}'")
            
            # Handle added parameters (these were added by the generator, so we remove them)
            if "added" in version_data:
                params_to_remove = []
                for addition in version_data["added"]:
                    if addition[0] == "parameters":
                        param_data = addition[1]
                        param_name = param_data.get("parameter_name")
                        # Find and mark for removal
                        for idx, param in enumerate(template_doc.parameters):
                            if param.parameter_name == param_name:
                                params_to_remove.append(idx)
                                print(f"  - Removing added parameter '{param_name}'")
                                break
                
                # Remove in reverse order to maintain indices
                for idx in sorted(params_to_remove, reverse=True):
                    template_doc.parameters.pop(idx)
            
            # Save the restored template
            template_doc.flags.ignore_version = True
            template_doc.save(ignore_permissions=True)
            frappe.db.commit()
            
            print(f"✅ Successfully restored '{template_name}'")
            restored.append(template_name)
            
        except Exception as e:
            error_msg = f"❌ Error restoring '{template_name}': {str(e)}"
            print(error_msg)
            import traceback
            print(traceback.format_exc())
            errors.append({"template": template_name, "error": str(e)})
    
    print("\n" + "="*60)
    print("RESTORATION SUMMARY")
    print("="*60)
    print(f"✅ Successfully restored: {len(restored)} templates")
    if restored:
        for t in restored:
            print(f"   - {t}")
    
    if errors:
        print(f"\n❌ Errors: {len(errors)}")
        for err in errors:
            print(f"   - {err['template']}: {err['error']}")
    
    return {"restored": restored, "errors": errors}

if __name__ == "__main__":
    frappe.init(site="rockettradeline.com")
    frappe.connect()
    result = apply_version_data()
    frappe.destroy()

import frappe

def execute():
    """
    Migration to create Allowed File Name records for existing hardcoded file names
    """
    
    # List of existing allowed file names with their descriptions and categories
    file_names_data = [
        {
            "file_name": "dl_front",
            "description": "Front side of driver's license",
            "category": "Identity"
        },
        {
            "file_name": "dl_back", 
            "description": "Back side of driver's license",
            "category": "Identity"
        },
        {
            "file_name": "proof_of_address",
            "description": "Document proving current address",
            "category": "Address Proof"
        },
        {
            "file_name": "client_signature",
            "description": "Client's digital signature",
            "category": "Signature"
        },
        {
            "file_name": "proof_of_enrollment",
            "description": "Proof of enrollment in tradeline program",
            "category": "Proof Documents"
        },
        {
            "file_name": "proof_of_refund",
            "description": "Proof of refund documentation",
            "category": "Proof Documents"
        },
        {
            "file_name": "credit_report",
            "description": "Credit report document",
            "category": "Proof Documents"
        },
        {
            "file_name": "authorized_user_guide",
            "description": "Guide for authorized users",
            "category": "Other"
        },
        {
            "file_name": "privacy_policy",
            "description": "Privacy policy document",
            "category": "Policy Documents"
        },
        {
            "file_name": "terms_conditions",
            "description": "Terms and conditions document", 
            "category": "Policy Documents"
        },
        {
            "file_name": "refund_policy",
            "description": "Refund policy document",
            "category": "Policy Documents"
        },
        {
            "file_name": "authorized_user_agreement",
            "description": "Authorized user agreement document",
            "category": "Policy Documents"
        }
    ]
    
    print("Creating Allowed File Name records...")
    
    for file_data in file_names_data:
        try:
            # Check if record already exists
            if not frappe.db.exists("Allowed File Name", file_data["file_name"]):
                doc = frappe.get_doc({
                    "doctype": "Allowed File Name",
                    "file_name": file_data["file_name"],
                    "description": file_data["description"],
                    "category": file_data["category"],
                    "is_active": 1
                })
                
                doc.insert(ignore_permissions=True)
                print(f"Created: {file_data['file_name']}")
            else:
                print(f"Already exists: {file_data['file_name']}")
                
        except Exception as e:
            print(f"Error creating {file_data['file_name']}: {str(e)}")
    
    frappe.db.commit()
    print("Migration completed successfully!")
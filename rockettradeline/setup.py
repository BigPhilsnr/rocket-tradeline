import frappe
from frappe import _

def after_install():
    """
    Setup roles and permissions after app installation
    """
    setup_custom_roles()
    setup_permissions()
    create_default_site_content()
    print("Rockettradeline app installation completed successfully!")

def setup_custom_roles():
    """
    Create custom roles for the app
    """
    roles = [
        {
            "role_name": "Tradeline Manager",
            "desk_access": 1,
            "description": "Can manage tradelines and related data"
        },
        {
            "role_name": "Website Manager", 
            "desk_access": 1,
            "description": "Can manage website content and settings"
        },
        {
            "role_name": "Customer",
            "desk_access": 0,
            "description": "Website customer role"
        }
    ]
    
    for role_data in roles:
        if not frappe.db.exists("Role", role_data["role_name"]):
            role = frappe.get_doc({
                "doctype": "Role",
                "role_name": role_data["role_name"],
                "desk_access": role_data["desk_access"],
                "description": role_data.get("description", "")
            })
            role.insert(ignore_permissions=True)
            print(f"Created role: {role_data['role_name']}")

def setup_permissions():
    """
    Setup permissions for doctypes
    """
    # Permissions for Tradeline
    tradeline_permissions = [
        {"role": "System Manager", "perms": ["read", "write", "create", "delete", "submit", "cancel", "amend"]},
        {"role": "Tradeline Manager", "perms": ["read", "write", "create", "delete"]},
        {"role": "Customer", "perms": ["read"]}
    ]
    
    setup_doctype_permissions("Tradeline", tradeline_permissions)
    
    # Permissions for Tradeline Bank
    bank_permissions = [
        {"role": "System Manager", "perms": ["read", "write", "create", "delete"]},
        {"role": "Tradeline Manager", "perms": ["read", "write", "create", "delete"]},
        {"role": "Customer", "perms": ["read"]}
    ]
    
    setup_doctype_permissions("Tradeline Bank", bank_permissions)
    
    # Permissions for Card Holder
    card_holder_permissions = [
        {"role": "System Manager", "perms": ["read", "write", "create", "delete"]},
        {"role": "Tradeline Manager", "perms": ["read", "write", "create", "delete"]}
    ]
    
    setup_doctype_permissions("Card Holder", card_holder_permissions)
    
    # Permissions for Site Content are already set up in the doctype definition
    
    # Permissions for FAQ
    faq_permissions = [
        {"role": "System Manager", "perms": ["read", "write", "create", "delete"]},
        {"role": "Website Manager", "perms": ["read", "write", "create", "delete"]},
        {"role": "Customer", "perms": ["read"]}
    ]
    
    setup_doctype_permissions("FAQ", faq_permissions)
    
    # Permissions for Testimonial
    testimonial_permissions = [
        {"role": "System Manager", "perms": ["read", "write", "create", "delete"]},
        {"role": "Website Manager", "perms": ["read", "write", "create", "delete"]},
        {"role": "Customer", "perms": ["read"]}
    ]
    
    setup_doctype_permissions("Testimonial", testimonial_permissions)
    
    # Permissions for Page Content
    page_content_permissions = [
        {"role": "System Manager", "perms": ["read", "write", "create", "delete"]},
        {"role": "Website Manager", "perms": ["read", "write", "create", "delete"]},
        {"role": "Customer", "perms": ["read"]}
    ]
    
    setup_doctype_permissions("Page Content", page_content_permissions)

def setup_doctype_permissions(doctype, permissions):
    """
    Setup permissions for a specific doctype
    """
    for perm in permissions:
        role = perm["role"]
        perms = perm["perms"]
        
        # Check if permission already exists
        existing_perm = frappe.db.get_value("Custom DocPerm", {
            "parent": doctype,
            "role": role
        })
        
        if not existing_perm:
            doc_perm = frappe.get_doc({
                "doctype": "Custom DocPerm",
                "parent": doctype,
                "parenttype": "DocType",
                "parentfield": "permissions",
                "role": role,
                "read": 1 if "read" in perms else 0,
                "write": 1 if "write" in perms else 0,
                "create": 1 if "create" in perms else 0,
                "delete": 1 if "delete" in perms else 0,
                "submit": 1 if "submit" in perms else 0,
                "cancel": 1 if "cancel" in perms else 0,
                "amend": 1 if "amend" in perms else 0
            })
            doc_perm.insert(ignore_permissions=True)
            print(f"Created permission for {doctype} - {role}")

def create_default_site_content():
    """
    Create default site content
    """
    default_content = [
        {
            "key": "site_title",
            "value": "Rocket Tradeline",
            "section": "website",
            "page": "general",
            "content_type": "Text"
        },
        {
            "key": "site_description", 
            "value": "Premium tradeline services to boost your credit score",
            "section": "website",
            "page": "general",
            "content_type": "Text"
        },
        {
            "key": "meta_keywords",
            "value": "tradeline, credit, credit score, authorized user, credit repair",
            "section": "website",
            "page": "general", 
            "content_type": "Text"
        },
        {
            "key": "contact_email",
            "value": "info@rockettradeline.com",
            "section": "contact",
            "page": "general",
            "content_type": "Text"
        },
        {
            "key": "contact_phone",
            "value": "+1-800-123-4567",
            "section": "contact", 
            "page": "general",
            "content_type": "Text"
        },
        {
            "key": "footer_text",
            "value": "© 2025 Rocket Tradeline. All rights reserved.",
            "section": "website",
            "page": "general",
            "content_type": "HTML"
        }
    ]
    
    for content_data in default_content:
        if not frappe.db.exists("Site Content", content_data["key"]):
            content = frappe.get_doc({
                "doctype": "Site Content",
                **content_data,
                "is_active": 1
            })
            content.insert(ignore_permissions=True)
            print(f"Created site content: {content_data['key']}")
    
    print("Default site content created successfully!")

def create_sample_data():
    """
    Create sample data for demonstration
    """
    # Create sample banks
    sample_banks = [
        "Chase Bank",
        "Bank of America", 
        "Wells Fargo",
        "Capital One",
        "Citi Bank",
        "American Express"
    ]
    
    for bank_name in sample_banks:
        if not frappe.db.exists("Tradeline Bank", bank_name):
            bank = frappe.get_doc({
                "doctype": "Tradeline Bank",
                "bank_name": bank_name
            })
            bank.insert(ignore_permissions=True)
    
    # Create sample mailing address
    if not frappe.db.exists("Mailing Address", "Sample Address"):
        # You'd need to check the actual structure of Mailing Address doctype
        pass
    
    # Create sample card holder
    if not frappe.db.exists("Card Holder", "John Doe"):
        card_holder = frappe.get_doc({
            "doctype": "Card Holder",
            "fullname": "John Doe",
            "email": "john@example.com",
            "phone": "+1-555-123-4567"
        })
        card_holder.insert(ignore_permissions=True)
    
    # Create sample FAQs
    sample_faqs = [
        {
            "question": "What is a tradeline?",
            "answer": "A tradeline is a record of activity for any type of credit extended to you by a lender and reported to a credit reporting agency.",
            "category": "General"
        },
        {
            "question": "How long does it take to see results?",
            "answer": "Typically, you can see results within 30-45 days after being added as an authorized user.",
            "category": "Timeline"
        },
        {
            "question": "Is this service legal?",
            "answer": "Yes, authorized user tradelines are completely legal and have been used for decades.",
            "category": "Legal"
        }
    ]
    
    for faq_data in sample_faqs:
        if not frappe.db.exists("FAQ", faq_data["question"]):
            faq = frappe.get_doc({
                "doctype": "FAQ",
                "question": faq_data["question"],
                "answer": faq_data["answer"],
                "category": faq_data["category"],
                "is_published": 1
            })
            faq.insert(ignore_permissions=True)
    
    print("Sample data created successfully!")

if __name__ == "__main__":
    after_install()
    create_sample_data()

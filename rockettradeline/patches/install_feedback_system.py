"""
Install Tradeline Feedback DocType and Web Form
Patch to create the feedback system for RocketTradeline
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

def execute():
    """Install feedback system components"""
    
    # Install the doctype first
    frappe.reload_doc("rockettradeline", "doctype", "tradeline_feedback")
    
    # Install the web form
    frappe.reload_doc("rockettradeline", "web_form", "tradeline_feedback")
    
    # Create default email group for feedback notifications if needed
    if not frappe.db.exists("Email Group", "Feedback Notifications"):
        try:
            email_group = frappe.get_doc({
                "doctype": "Email Group",
                "title": "Feedback Notifications",
                "description": "Notifications for new feedback submissions"
            })
            email_group.insert(ignore_permissions=True)
            frappe.db.commit()
            print("✅ Created 'Feedback Notifications' email group")
        except Exception as e:
            print(f"❌ Error creating email group: {str(e)}")
    
    # Create sample data if in development
    if frappe.conf.get("developer_mode"):
        create_sample_feedback_data()
    
    print("✅ Tradeline Feedback system installed successfully!")

def create_sample_feedback_data():
    """Create sample feedback data for testing"""
    
    sample_data = [
        {
            "question_1_why_buying": "I want to buy a home or property",
            "question_2_importance": "Very Important", 
            "question_3_timeline": "Urgent (within 30 days)",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone": "+1234567890",
            "source": "Sample Data",
            "status": "New"
        },
        {
            "question_1_why_buying": "I want to buy a car",
            "question_2_importance": "Important",
            "question_3_timeline": "Next 1–2 months (31–60 days)",
            "first_name": "Jane",
            "last_name": "Smith", 
            "email": "jane.smith@example.com",
            "phone": "+1987654321",
            "source": "Sample Data",
            "status": "Contacted"
        }
    ]
    
    try:
        for data in sample_data:
            # Check if feedback with this email already exists
            existing = frappe.db.exists("Tradeline Feedback", {"email": data["email"]})
            if not existing:
                feedback = frappe.get_doc({
                    "doctype": "Tradeline Feedback",
                    **data
                })
                feedback.insert(ignore_permissions=True)
        
        frappe.db.commit()
        print("✅ Sample feedback data created")
        
    except Exception as e:
        print(f"❌ Error creating sample data: {str(e)}")

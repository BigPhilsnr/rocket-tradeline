# Example usage of Email Template Custom doctype

"""
This file shows examples of how to use the new Email Template Custom doctype
to replace hardcoded email content in auth.py and other modules.

Usage Examples:
"""

import frappe
from rockettradeline.utils.email_templates import send_email_from_template

# Example 1: Send verification email using template
def send_verification_email_new(user_email, full_name, verification_token):
    """Send email verification using custom template"""
    try:
        # Create verification link
        site_url = frappe.utils.get_url()
        verification_link = f"{site_url}/api/method/rockettradeline.api.auth.verify_email?token={verification_token}"
        
        # Prepare context for template
        context = {
            "full_name": full_name,
            "site_name": frappe.local.site,
            "verification_link": verification_link
        }
        
        # Send email using template
        result = send_email_from_template(
            template_name="Email Verification",
            recipients=[user_email],
            context=context,
            delayed=False,
            retry=3
        )
        
        return result["success"]
        
    except Exception as e:
        frappe.log_error(f"Verification email failed for {user_email}: {str(e)}", "Email Template Usage")
        return False


# Example 2: Send password reset email using template
def send_password_reset_email_new(user_email, full_name, reset_key):
    """Send password reset email using custom template"""
    try:
        # Create reset link
        site_url = frappe.utils.get_url()
        reset_link = f"{site_url}/reset-password?key={reset_key}"
        
        # Prepare context for template
        context = {
            "full_name": full_name,
            "site_name": frappe.local.site,
            "reset_link": reset_link
        }
        
        # Send email using template
        result = send_email_from_template(
            template_name="Password Reset",
            recipients=[user_email],
            context=context
        )
        
        return result["success"]
        
    except Exception as e:
        frappe.log_error(f"Password reset email failed for {user_email}: {str(e)}", "Email Template Usage")
        return False


# Example 3: Send payment confirmation email using template
def send_payment_confirmation_email(user_email, full_name, payment_data):
    """Send payment confirmation email using custom template"""
    try:
        # Prepare context for template
        context = {
            "full_name": full_name,
            "order_number": payment_data.get("order_number"),
            "amount": payment_data.get("amount"),
            "payment_method": payment_data.get("payment_method"),
            "transaction_id": payment_data.get("transaction_id")
        }
        
        # Send email using template
        result = send_email_from_template(
            template_name="Payment Confirmation",
            recipients=[user_email],
            context=context
        )
        
        return result["success"]
        
    except Exception as e:
        frappe.log_error(f"Payment confirmation email failed for {user_email}: {str(e)}", "Email Template Usage")
        return False


# Example 4: Create a custom template programmatically
def create_custom_welcome_template():
    """Example of creating a custom email template"""
    try:
        template = frappe.get_doc({
            "doctype": "Email Template Custom",
            "template_name": "Custom Welcome Email",
            "subject": "Welcome to {{company_name}}, {{full_name}}!",
            "description": "Custom welcome email for new customers",
            "template_type": "Welcome",
            "is_active": 1,
            "html_content": """
                <div style="margin-bottom: 25px;">
                    <h2 style="color: #17B26A; margin: 0 0 20px 0;">🎉 Welcome to {{company_name}}!</h2>
                    <p style="color: #374151; font-size: 16px; margin: 0 0 10px 0;">Hi {{full_name}},</p>
                    <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0;">
                        We're excited to have you join our community of tradeline buyers and sellers!
                    </p>
                </div>
                
                <div style="background-color: #f0f9ff; border-left: 4px solid #17B26A; padding: 20px; border-radius: 6px; margin: 25px 0;">
                    <h3 style="color: #374151; margin: 0 0 15px 0;">What's Next?</h3>
                    <ul style="margin: 0; padding-left: 20px; color: #6b7280; line-height: 1.6;">
                        <li style="margin: 8px 0;">Browse our available tradelines</li>
                        <li style="margin: 8px 0;">Complete your profile setup</li>
                        <li style="margin: 8px 0;">Start building your credit score</li>
                    </ul>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{{dashboard_link}}" style="background-color: #17B26A; color: white; padding: 12px 24px; text-decoration: none; 
                              border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">
                        Go to Dashboard
                    </a>
                </div>
                
                <div style="margin-top: 25px;">
                    <p style="color: #6b7280; margin: 0; font-size: 16px;">
                        If you have any questions, feel free to contact our support team.<br><br>
                        Welcome aboard!<br>
                        The {{company_name}} Team
                    </p>
                </div>
            """,
            "parameters": [
                {
                    "parameter_name": "full_name",
                    "parameter_label": "Full Name",
                    "parameter_type": "Data",
                    "is_required": 1,
                    "description": "Customer's full name"
                },
                {
                    "parameter_name": "company_name",
                    "parameter_label": "Company Name",
                    "parameter_type": "Data",
                    "is_required": 1,
                    "default_value": "RocketTradeline",
                    "description": "Company name"
                },
                {
                    "parameter_name": "dashboard_link",
                    "parameter_label": "Dashboard Link",
                    "parameter_type": "Data",
                    "is_required": 1,
                    "description": "Link to customer dashboard"
                }
            ]
        })
        
        template.insert()
        return template.name
        
    except Exception as e:
        frappe.log_error(f"Error creating custom welcome template: {str(e)}", "Template Creation")
        return None


# Example 5: Using template with custom formatting
def send_formatted_notification(recipients, template_name, **kwargs):
    """Generic function to send formatted emails using templates"""
    try:
        result = send_email_from_template(
            template_name=template_name,
            recipients=recipients,
            context=kwargs
        )
        
        if result["success"]:
            frappe.logger().info(f"Email sent successfully using template '{template_name}' to {recipients}")
        else:
            frappe.logger().error(f"Email failed using template '{template_name}': {result.get('error')}")
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Formatted email notification failed: {str(e)}", "Email Notification")
        return {"success": False, "error": str(e)}


"""
To replace existing hardcoded emails in auth.py:

1. Replace send_verification_email() with send_verification_email_new()
2. Replace send_reset_password_link() content with send_password_reset_email_new()
3. Create payment confirmation emails using send_payment_confirmation_email()

Benefits:
- Centralized email management
- Easy to update email content without code changes
- Template versioning and backup
- Parameter validation
- Consistent branding across all emails
- A/B testing capabilities
- Non-technical staff can update email content
"""
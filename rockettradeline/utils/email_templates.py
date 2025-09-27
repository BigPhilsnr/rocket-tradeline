# Copyright (c) 2025, RocketTradeline and contributors
# Email Template Utilities

import frappe
from frappe import _


def send_email_from_template(template_name, recipients, context=None, **kwargs):
    """
    Send email using custom email template
    
    Args:
        template_name (str): Name of the email template
        recipients (str|list): Email recipient(s)
        context (dict): Context variables for template rendering
        **kwargs: Additional arguments for frappe.sendmail
    
    Returns:
        dict: Response with success status and message
    """
    try:
        # Get the template
        template = frappe.get_doc("Email Template Custom", template_name)
        
        if not template.is_active:
            return {
                "success": False,
                "error": "Email template is not active"
            }
        
        # Ensure recipients is a list
        if isinstance(recipients, str):
            recipients = [recipients]
        
        # Send email using template
        success = template.send_email(recipients, context, **kwargs)
        
        return {
            "success": success,
            "message": "Email sent successfully" if success else "Email sending failed"
        }
        
    except Exception as e:
        frappe.log_error(f"Email template sending failed: {str(e)}", "Email Template Utility")
        return {
            "success": False,
            "error": str(e)
        }


def get_template_list(template_type=None, is_active=True):
    """
    Get list of available email templates
    
    Args:
        template_type (str): Filter by template type
        is_active (bool): Filter by active status
    
    Returns:
        list: List of templates
    """
    try:
        filters = {}
        
        if template_type:
            filters["template_type"] = template_type
        
        if is_active is not None:
            filters["is_active"] = is_active
        
        templates = frappe.get_all("Email Template Custom",
            filters=filters,
            fields=["name", "template_name", "subject", "description", "template_type", "is_active"],
            order_by="template_name"
        )
        
        return {
            "success": True,
            "templates": templates
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def create_default_templates():
    """Create default email templates"""
    
    default_templates = [
        {
            "template_name": "Email Verification",
            "subject": "Verify Your Email Address - {{site_name}}",
            "description": "Email verification template for new user registration",
            "template_type": "Verification",
            "html_content": """
                <div style="margin-bottom: 25px;">
                    <p style="color: #374151; font-size: 16px; margin: 0 0 10px 0;">Hi {{full_name}},</p>
                    <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0;">
                        You just signed up for an account at {{site_name}}. To complete your registration and buy tradelines, click the button below.
                    </p>
                </div>
                
                <!-- Verify Button -->
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{{verification_link}}" style="background-color: #17B26A; color: white; padding: 12px 24px; text-decoration: none; 
                              border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">
                        Verify email
                    </a>
                </div>
                
                <div style="margin-top: 25px;">
                    <p style="color: #6b7280; margin: 0; font-size: 16px;">
                        Thanks,<br>
                        The team
                    </p>
                </div>
            """,
            "parameters": [
                {"parameter_name": "full_name", "parameter_label": "Full Name", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "site_name", "parameter_label": "Site Name", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "verification_link", "parameter_label": "Verification Link", "parameter_type": "Data", "is_required": 1}
            ]
        },
        {
            "template_name": "Password Reset",
            "subject": "Reset Your Password - {{site_name}}",
            "description": "Password reset email template",
            "template_type": "Password Reset",
            "html_content": """
                <div style="margin-bottom: 25px;">
                    <p style="color: #374151; font-size: 16px; margin: 0 0 10px 0;">Hi {{full_name}},</p>
                    <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0;">
                        We received a request to reset your password for your {{site_name}} account.
                    </p>
                </div>
                
                <!-- Reset Button -->
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{{reset_link}}" style="background-color: #17B26A; color: white; padding: 12px 24px; text-decoration: none; 
                              border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">
                        Reset Password
                    </a>
                </div>
                
                <div style="background-color: #f9fafb; border-left: 4px solid #6b7280; padding: 15px; border-radius: 6px; margin: 25px 0;">
                    <p style="margin: 0; color: #374151; font-size: 14px;">
                        This link will expire in 24 hours. If you didn't request this password reset, please ignore this email.
                    </p>
                </div>
                
                <div style="margin-top: 25px;">
                    <p style="color: #6b7280; margin: 0; font-size: 16px;">
                        Thanks,<br>
                        The team
                    </p>
                </div>
            """,
            "parameters": [
                {"parameter_name": "full_name", "parameter_label": "Full Name", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "site_name", "parameter_label": "Site Name", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "reset_link", "parameter_label": "Reset Link", "parameter_type": "Data", "is_required": 1}
            ]
        },
        {
            "template_name": "Payment Confirmation",
            "subject": "Payment Confirmation - Order #{{order_number}}",
            "description": "Payment confirmation email template",
            "template_type": "Payment Confirmation",
            "html_content": """
                <div style="margin-bottom: 25px;">
                    <p style="color: #374151; font-size: 16px; margin: 0 0 10px 0;">Hi {{full_name}},</p>
                    <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0;">
                        Thank you for your payment! We've successfully received your payment for order #{{order_number}}.
                    </p>
                </div>
                
                <!-- Payment Details -->
                <div style="background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px; padding: 20px; margin: 25px 0;">
                    <h3 style="color: #374151; margin: 0 0 15px 0;">Payment Details</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Order Number:</td>
                            <td style="padding: 8px 0; color: #374151; font-weight: 600;">{{order_number}}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Amount Paid:</td>
                            <td style="padding: 8px 0; color: #374151; font-weight: 600;">${{amount}}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Payment Method:</td>
                            <td style="padding: 8px 0; color: #374151; font-weight: 600;">{{payment_method}}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Transaction ID:</td>
                            <td style="padding: 8px 0; color: #374151; font-weight: 600;">{{transaction_id}}</td>
                        </tr>
                    </table>
                </div>
                
                <div style="margin-top: 25px;">
                    <p style="color: #6b7280; margin: 0; font-size: 16px;">
                        Your tradelines will be processed within 1-2 business days.<br><br>
                        Thanks,<br>
                        The team
                    </p>
                </div>
            """,
            "parameters": [
                {"parameter_name": "full_name", "parameter_label": "Full Name", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "order_number", "parameter_label": "Order Number", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "amount", "parameter_label": "Amount", "parameter_type": "Float", "is_required": 1},
                {"parameter_name": "payment_method", "parameter_label": "Payment Method", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "transaction_id", "parameter_label": "Transaction ID", "parameter_type": "Data", "is_required": 1}
            ]
        }
    ]
    
    created_templates = []
    
    for template_data in default_templates:
        try:
            # Check if template already exists
            if frappe.db.exists("Email Template Custom", template_data["template_name"]):
                print(f"Template '{template_data['template_name']}' already exists, skipping...")
                continue
            
            # Extract parameters for separate handling
            parameters = template_data.pop("parameters", [])
            
            # Create template document
            template = frappe.get_doc({
                "doctype": "Email Template Custom",
                **template_data
            })
            
            # Add parameters as child table rows
            for param in parameters:
                template.append("parameters", param)
            
            # Insert the template
            template.insert(ignore_permissions=True)
            frappe.db.commit()
            
            created_templates.append(template_data["template_name"])
            print(f"Created template: {template_data['template_name']}")
            
        except Exception as e:
            error_msg = f"Error creating template {template_data['template_name']}: {str(e)}"
            print(error_msg)
            frappe.log_error(error_msg, "Default Template Creation")
    
    return created_templates


# API endpoints for managing email templates

@frappe.whitelist()
def get_email_templates(template_type=None):
    """API endpoint to get email templates"""
    return get_template_list(template_type)


@frappe.whitelist()
def send_template_email_api(template_name, recipients, context=None):
    """API endpoint to send email using template"""
    if isinstance(context, str):
        import json
        context = json.loads(context)
    
    return send_email_from_template(template_name, recipients, context)


@frappe.whitelist()
def preview_email_template(template_name, context=None):
    """API endpoint to preview email template"""
    try:
        template = frappe.get_doc("Email Template Custom", template_name)
        
        if isinstance(context, str):
            import json
            context = json.loads(context)
        
        subject, content = template.get_rendered_content(context)
        
        # Import header and footer functions for preview
        from rockettradeline.api.auth import get_email_header, get_email_footer
        
        # Use a sample email for footer
        sample_email = context.get('recipient_email', 'sample@example.com') if context else 'sample@example.com'
        email_header = get_email_header()
        email_footer = get_email_footer(sample_email)
        full_content = f"{email_header}{content}{email_footer}"
        
        return {
            "success": True,
            "subject": subject,
            "content": content,
            "full_content": full_content
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
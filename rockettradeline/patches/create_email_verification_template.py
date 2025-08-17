import frappe

def execute():
    """Create email verification template"""
    
    # Check if template already exists
    if frappe.db.exists("Email Template", "Email Verification"):
        return
    
    # Create email template
    template = frappe.get_doc({
        "doctype": "Email Template",
        "name": "Email Verification",
        "subject": "Verify Your Email Address - {{ site_name }}",
        "response": """
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
    <div style="background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #2563eb; margin: 0; font-size: 28px;">Welcome to {{ site_name }}!</h1>
        </div>
        
        <div style="margin-bottom: 30px;">
            <h2 style="color: #374151; margin-bottom: 15px;">Hi {{ full_name }},</h2>
            <p style="color: #6b7280; line-height: 1.6; font-size: 16px;">
                Thank you for signing up! To complete your registration and secure your account, 
                please verify your email address by clicking the button below.
            </p>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{{ verification_link }}" 
               style="background-color: #2563eb; color: white; padding: 15px 30px; text-decoration: none; 
                      border-radius: 8px; font-weight: bold; font-size: 16px; display: inline-block;
                      box-shadow: 0 4px 6px rgba(37, 99, 235, 0.3);">
                Verify Email Address
            </a>
        </div>
        
        <div style="margin: 30px 0; padding: 20px; background-color: #f3f4f6; border-radius: 8px;">
            <p style="color: #6b7280; margin: 0; font-size: 14px;">
                <strong>Note:</strong> This verification link will expire in 24 hours for security reasons.
                If the button doesn't work, you can copy and paste this link into your browser:
            </p>
            <p style="color: #2563eb; word-break: break-all; margin: 10px 0 0 0; font-size: 14px;">
                {{ verification_link }}
            </p>
        </div>
        
        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
            <p style="color: #9ca3af; font-size: 14px; margin: 0;">
                If you didn't create an account with us, please ignore this email.
            </p>
            <p style="color: #9ca3af; font-size: 14px; margin: 10px 0 0 0;">
                Best regards,<br>
                The {{ site_name }} Team
            </p>
        </div>
    </div>
</div>
        """,
        "use_html": 1,
        "enabled": 1
    })
    
    template.insert()
    frappe.db.commit()
    
    print("Email verification template created successfully!")

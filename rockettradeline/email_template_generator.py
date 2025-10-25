# Copyright (c) 2025, RocketTradeline and contributors
# Email Template Generator for RocketTradeline App

import frappe
from frappe.utils import now_datetime


def generate_email_templates():
    """
    Generate and insert all email templates for RocketTradeline app
    """
    
    templates = [
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
                        The RocketTradeline team
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
                        We received a request to reset your password for your {{site_name}} account. If you made this request, click the button below to reset your password.
                    </p>
                </div>
                
                <!-- Reset Button -->
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{{reset_link}}" style="background-color: #17B26A; color: white; padding: 12px 24px; text-decoration: none; 
                              border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">
                        Reset Your Password
                    </a>
                </div>
                
                <div style="background-color: #f9fafb; border-left: 4px solid #17B26A; padding: 15px; border-radius: 6px; margin: 25px 0;">
                    <p style="margin: 0 0 10px 0; color: #374151; font-weight: 600;">
                        🔒 Security Information:
                    </p>
                    <ul style="margin: 0; padding-left: 20px; color: #6b7280; line-height: 1.6; font-size: 14px;">
                        <li style="margin: 5px 0;">This link will expire in 24 hours for security reasons</li>
                        <li style="margin: 5px 0;">You can only use this link once</li>
                        <li style="margin: 5px 0;">If you didn't request this reset, please ignore this email</li>
                    </ul>
                </div>
                
                <div style="margin-top: 25px;">
                    <p style="color: #6b7280; margin: 0; font-size: 16px;">
                        Thanks,<br>
                        The RocketTradeline team
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
                        The RocketTradeline team
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
        },
        {
            "template_name": "Welcome Email",
            "subject": "Welcome to RocketTradeline - {{full_name}}",
            "description": "Welcome email for new users after email verification",
            "template_type": "Welcome",
            "html_content": """
                <div style="margin-bottom: 25px;">
                    <p style="color: #374151; font-size: 16px; margin: 0 0 10px 0;">Welcome {{full_name}}!</p>
                    <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0;">
                        Your email has been verified and your RocketTradeline account is now active. You can start exploring our tradeline marketplace and boost your credit score.
                    </p>
                </div>
                
                <!-- Features Section -->
                <div style="background-color: #f0f9ff; border-left: 4px solid #17B26A; padding: 20px; border-radius: 6px; margin: 25px 0;">
                    <h3 style="color: #374151; margin: 0 0 15px 0;">What you can do now:</h3>
                    <ul style="margin: 0; padding-left: 20px; color: #6b7280; line-height: 1.6;">
                        <li style="margin: 8px 0;">Browse our extensive tradeline marketplace</li>
                        <li style="margin: 8px 0;">Choose tradelines that fit your credit goals</li>
                        <li style="margin: 8px 0;">Complete your purchase securely</li>
                        <li style="margin: 8px 0;">Track your credit improvement</li>
                    </ul>
                </div>
                
                <!-- Get Started Button -->
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{{dashboard_link}}" style="background-color: #17B26A; color: white; padding: 12px 24px; text-decoration: none; 
                              border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">
                        Get Started
                    </a>
                </div>
                
                <div style="margin-top: 25px;">
                    <p style="color: #6b7280; margin: 0; font-size: 16px;">
                        If you have any questions, our support team is here to help at {{support_email}}.<br><br>
                        Thanks,<br>
                        The RocketTradeline team
                    </p>
                </div>
            """,
            "parameters": [
                {"parameter_name": "full_name", "parameter_label": "Full Name", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "dashboard_link", "parameter_label": "Dashboard Link", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "support_email", "parameter_label": "Support Email", "parameter_type": "Data", "is_required": 1, "default_value": "info@rockettradeline.com"}
            ]
        },
        {
            "template_name": "Order Shipped",
            "subject": "Your Tradeline Order is Being Processed - Order #{{order_number}}",
            "description": "Notification when tradeline order is being processed",
            "template_type": "Notification",
            "html_content": """
                <div style="margin-bottom: 25px;">
                    <p style="color: #374151; font-size: 16px; margin: 0 0 10px 0;">Hi {{full_name}},</p>
                    <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0;">
                        Great news! Your tradeline order #{{order_number}} is now being processed and will be added to your credit report shortly.
                    </p>
                </div>
                
                <!-- Order Details -->
                <div style="background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px; padding: 20px; margin: 25px 0;">
                    <h3 style="color: #374151; margin: 0 0 15px 0;">Order Details</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Order Number:</td>
                            <td style="padding: 8px 0; color: #374151; font-weight: 600;">{{order_number}}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Tradeline Bank:</td>
                            <td style="padding: 8px 0; color: #374151; font-weight: 600;">{{tradeline_bank}}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Credit Limit:</td>
                            <td style="padding: 8px 0; color: #374151; font-weight: 600;">${{credit_limit}}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Expected Reporting Date:</td>
                            <td style="padding: 8px 0; color: #374151; font-weight: 600;">{{reporting_date}}</td>
                        </tr>
                    </table>
                </div>
                
                <!-- Next Steps -->
                <div style="background-color: #fef3c7; border: 1px solid #fbbf24; padding: 15px; border-radius: 6px; margin: 25px 0;">
                    <p style="margin: 0; color: #92400e; font-weight: 600; font-size: 14px;">
                        📅 Next Steps: Your tradeline will appear on your credit report within {{processing_days}} business days.
                    </p>
                </div>
                
                <div style="margin-top: 25px;">
                    <p style="color: #6b7280; margin: 0; font-size: 16px;">
                        You'll receive another email once the tradeline appears on your credit report.<br><br>
                        Thanks,<br>
                        The RocketTradeline team
                    </p>
                </div>
            """,
            "parameters": [
                {"parameter_name": "full_name", "parameter_label": "Full Name", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "order_number", "parameter_label": "Order Number", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "tradeline_bank", "parameter_label": "Tradeline Bank", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "credit_limit", "parameter_label": "Credit Limit", "parameter_type": "Float", "is_required": 1},
                {"parameter_name": "reporting_date", "parameter_label": "Reporting Date", "parameter_type": "Date", "is_required": 1},
                {"parameter_name": "processing_days", "parameter_label": "Processing Days", "parameter_type": "Int", "is_required": 1, "default_value": "5-7"}
            ]
        },
        {
            "template_name": "Account Setup Required",
            "subject": "Complete Your Account Setup - Signature Required",
            "description": "Client signature request email for broker-created accounts",
            "template_type": "Verification",
            "html_content": """
                <div style="margin-bottom: 25px;">
                    <h3 style="color: #374151; margin: 0 0 20px 0;">📝 Complete Your Account Setup</h3>
                    <p style="color: #374151; font-size: 16px; margin: 0 0 10px 0;">Hello {{full_name}},</p>
                    <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0 0 25px 0;">
                        Your RocketTradeline account has been created by your broker. To complete your account setup and start purchasing tradelines, we need your digital signature.
                    </p>
                </div>
                
                <div style="background-color: #f0f9ff; border-left: 4px solid #17B26A; padding: 20px; border-radius: 6px; margin: 25px 0;">
                    <h4 style="color: #374151; margin: 0 0 15px 0;">What you need to do:</h4>
                    <ul style="margin: 0; padding-left: 20px; color: #6b7280; line-height: 1.6;">
                        <li style="margin: 8px 0;">Click the "Complete Setup" button below</li>
                        <li style="margin: 8px 0;">Upload your digital signature</li>
                        <li style="margin: 8px 0;">Start purchasing tradelines immediately</li>
                    </ul>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{{signature_link}}" 
                       style="background-color: #17B26A; color: white; padding: 14px 28px; text-decoration: none; 
                              border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">
                        Complete Account Setup
                    </a>
                </div>
                
                <div style="background-color: #f9fafb; border-left: 4px solid #6b7280; padding: 15px; border-radius: 6px; margin: 25px 0;">
                    <p style="margin: 0 0 10px 0; color: #374151; font-weight: 600;">
                        🔒 Security Information:
                    </p>
                    <ul style="margin: 0; padding-left: 20px; color: #6b7280; line-height: 1.6; font-size: 14px;">
                        <li style="margin: 5px 0;">This link will expire in 24 hours for security reasons</li>
                        <li style="margin: 5px 0;">You can only use this link once</li>
                        <li style="margin: 5px 0;">Your signature will be securely stored and encrypted</li>
                    </ul>
                </div>
                
                <div style="background-color: #fef3c7; border: 1px solid #fbbf24; padding: 15px; border-radius: 6px; margin: 25px 0;">
                    <p style="margin: 0; color: #92400e; font-weight: 600; font-size: 14px;">
                        ⏰ Important: Complete your signature within 24 hours to activate your account.
                    </p>
                </div>
                
                <div style="margin-top: 25px;">
                    <p style="color: #6b7280; margin: 0; font-size: 16px;">
                        If you need assistance, please contact your broker or our support team at {{support_email}}<br><br>
                        Thanks,<br>
                        The RocketTradeline team
                    </p>
                </div>
            """,
            "parameters": [
                {"parameter_name": "full_name", "parameter_label": "Full Name", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "signature_link", "parameter_label": "Signature Link", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "support_email", "parameter_label": "Support Email", "parameter_type": "Data", "is_required": 1, "default_value": "info@rockettradeline.com"}
            ]
        },
        {
            "template_name": "Payment Failed",
            "subject": "Payment Failed - Order #{{order_number}}",
            "description": "Notification when payment fails",
            "template_type": "Notification",
            "html_content": """
                <div style="margin-bottom: 25px;">
                    <p style="color: #374151; font-size: 16px; margin: 0 0 10px 0;">Hi {{full_name}},</p>
                    <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0;">
                        We were unable to process your payment for order #{{order_number}}. Please review the details below and try again.
                    </p>
                </div>
                
                <!-- Payment Details -->
                <div style="background-color: #fef2f2; border: 1px solid #fecaca; border-radius: 6px; padding: 20px; margin: 25px 0;">
                    <h3 style="color: #DC2626; margin: 0 0 15px 0;">⚠️ Payment Failed</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Order Number:</td>
                            <td style="padding: 8px 0; color: #374151; font-weight: 600;">{{order_number}}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Amount:</td>
                            <td style="padding: 8px 0; color: #374151; font-weight: 600;">${{amount}}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Payment Method:</td>
                            <td style="padding: 8px 0; color: #374151; font-weight: 600;">{{payment_method}}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #6b7280;">Failure Reason:</td>
                            <td style="padding: 8px 0; color: #DC2626; font-weight: 600;">{{failure_reason}}</td>
                        </tr>
                    </table>
                </div>
                
                <!-- Retry Payment Button -->
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{{retry_payment_link}}" style="background-color: #17B26A; color: white; padding: 12px 24px; text-decoration: none; 
                              border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">
                        Retry Payment
                    </a>
                </div>
                
                <!-- Help Section -->
                <div style="background-color: #f0f9ff; border-left: 4px solid #17B26A; padding: 15px; border-radius: 6px; margin: 25px 0;">
                    <p style="margin: 0 0 10px 0; color: #374151; font-weight: 600;">
                        💡 Common Solutions:
                    </p>
                    <ul style="margin: 0; padding-left: 20px; color: #6b7280; line-height: 1.6; font-size: 14px;">
                        <li style="margin: 5px 0;">Check that your card details are correct</li>
                        <li style="margin: 5px 0;">Ensure you have sufficient funds available</li>
                        <li style="margin: 5px 0;">Contact your bank if the issue persists</li>
                    </ul>
                </div>
                
                <div style="margin-top: 25px;">
                    <p style="color: #6b7280; margin: 0; font-size: 16px;">
                        If you continue to experience issues, please contact our support team at {{support_email}}<br><br>
                        Thanks,<br>
                        The RocketTradeline team
                    </p>
                </div>
            """,
            "parameters": [
                {"parameter_name": "full_name", "parameter_label": "Full Name", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "order_number", "parameter_label": "Order Number", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "amount", "parameter_label": "Amount", "parameter_type": "Float", "is_required": 1},
                {"parameter_name": "payment_method", "parameter_label": "Payment Method", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "failure_reason", "parameter_label": "Failure Reason", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "retry_payment_link", "parameter_label": "Retry Payment Link", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "support_email", "parameter_label": "Support Email", "parameter_type": "Data", "is_required": 1, "default_value": "info@rockettradeline.com"}
            ]
        },
        {
            "template_name": "Cardholder Removal Required",
            "subject": "Client Removal Required - {{bank_name}} Expired",
            "description": "Email notification to cardholder to remove expired client from tradeline",
            "template_type": "Notification",
            "html_content": """
                <h3 style="color: #DC2626; margin: 0 0 20px 0;">Client Tradeline Expired - Removal Required</h3>
                <p style="color: #374151; font-size: 16px; margin: 0 0 10px 0;">Dear {{cardholder_name}},</p>
                
                <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0 0 25px 0;">
                    A client's tradeline subscription has expired and requires immediate attention. Please remove the following client from your tradeline as soon as possible.
                </p>
                
                <h4 style="color: #374151; margin: 20px 0 15px 0;">Client Removal Details:</h4>
                <div style="background-color: #fef2f2; border-left: 4px solid #DC2626; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
                    <p style="margin: 5px 0;"><strong>Client Name:</strong> {{customer_name}}</p>
                    <p style="margin: 5px 0;"><strong>Client Email:</strong> {{client_email}}</p>
                    <p style="margin: 5px 0;"><strong>Tradeline ID:</strong> {{tradeline_id}}</p>
                    <p style="margin: 5px 0;"><strong>Expired Date:</strong> {{expiry_date}}</p>
                    <p style="margin: 5px 0;"><strong>Duration:</strong> {{days_overdue}} days overdue</p>
                </div>
                
                <h4 style="color: #374151; margin: 20px 0 15px 0;">Tradeline Information:</h4>
                <div style="background-color: #f9fafb; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
                    <p style="margin: 5px 0;"><strong>Bank:</strong> {{bank_name}}</p>
                    <p style="margin: 5px 0;"><strong>Credit Limit:</strong> ${{credit_limit}}</p>
                    <p style="margin: 5px 0;"><strong>Account Age:</strong> {{age_year}} years {{age_month}} months</p>
                    <p style="margin: 5px 0;"><strong>Closing Date:</strong> {{closing_date}}</p>
                    <p style="margin: 5px 0;"><strong>Spots Purchased:</strong> {{quantity}}</p>
                    <p style="margin: 5px 0;"><strong>Amount Paid:</strong> ${{total_amount}}</p>
                </div>
                
                <h4 style="color: #374151; margin: 20px 0 15px 0;">Required Actions:</h4>
                <div style="background-color: #fff7ed; border-left: 4px solid #F59E0B; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
                    <ol style="margin: 0; padding-left: 20px; color: #6b7280; line-height: 1.6;">
                        <li style="margin: 5px 0;"><strong>Remove the client</strong> as an authorized user from your credit card account</li>
                        <li style="margin: 5px 0;"><strong>Update your account</strong> to reflect the removal</li>
                        <li style="margin: 5px 0;"><strong>Verify removal</strong> within 3-5 business days</li>
                        <li style="margin: 5px 0;"><strong>Contact support</strong> if you need assistance with the removal process</li>
                    </ol>
                </div>
                
                <div style="background-color: #fef2f2; border: 1px solid #fecaca; padding: 15px; border-radius: 6px; margin: 25px 0;">
                    <p style="margin: 0; color: #DC2626; font-weight: 600; font-size: 14px;">
                        ⚠️ Important: Failure to remove expired clients promptly may affect your tradeline performance and future earnings.
                    </p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://rocket-app.tiberbuhealth.com/app" 
                       style="background-color: #DC2626; color: white; padding: 12px 24px; text-decoration: none; 
                              border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">
                        Access Seller Portal
                    </a>
                </div>
                
                <p style="color: #6b7280; margin: 25px 0 0 0; font-size: 16px;">
                    If you have any questions about the removal process, please contact our support team immediately.
                </p>
            """,
            "parameters": [
                {"parameter_name": "cardholder_name", "parameter_label": "Cardholder Name", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "customer_name", "parameter_label": "Customer Name", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "client_email", "parameter_label": "Client Email", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "tradeline_id", "parameter_label": "Tradeline ID", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "expiry_date", "parameter_label": "Expiry Date", "parameter_type": "Date", "is_required": 1},
                {"parameter_name": "days_overdue", "parameter_label": "Days Overdue", "parameter_type": "Int", "is_required": 1},
                {"parameter_name": "bank_name", "parameter_label": "Bank Name", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "credit_limit", "parameter_label": "Credit Limit", "parameter_type": "Float", "is_required": 1},
                {"parameter_name": "age_year", "parameter_label": "Age Year", "parameter_type": "Int", "is_required": 1},
                {"parameter_name": "age_month", "parameter_label": "Age Month", "parameter_type": "Int", "is_required": 1},
                {"parameter_name": "closing_date", "parameter_label": "Closing Date", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "quantity", "parameter_label": "Quantity", "parameter_type": "Int", "is_required": 1},
                {"parameter_name": "total_amount", "parameter_label": "Total Amount", "parameter_type": "Float", "is_required": 1}
            ]
        },
        {
            "template_name": "Client Tradeline Expiration",
            "subject": "Tradeline Expired - {{bank_name}}",
            "description": "Email notification to client about tradeline expiration",
            "template_type": "Notification",
            "html_content": """
                <h3 style="color: #F59E0B; margin: 0 0 20px 0;">Your Tradeline Has Expired</h3>
                <p style="color: #374151; font-size: 16px; margin: 0 0 10px 0;">Dear {{customer_name}},</p>
                
                <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0 0 25px 0;">
                    Your tradeline subscription has reached its expiration date. Your authorized user status has been scheduled for removal from the tradeline account.
                </p>
                
                <h4 style="color: #374151; margin: 20px 0 15px 0;">Tradeline Summary:</h4>
                <div style="background-color: #f9fafb; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
                    <p style="margin: 5px 0;"><strong>Tradeline ID:</strong> {{tradeline_id}}</p>
                    <p style="margin: 5px 0;"><strong>Bank:</strong> {{bank_name}}</p>
                    <p style="margin: 5px 0;"><strong>Credit Limit:</strong> ${{credit_limit}}</p>
                    <p style="margin: 5px 0;"><strong>Account Age:</strong> {{age_year}} years {{age_month}} months</p>
                    <p style="margin: 5px 0;"><strong>Subscription Period:</strong> {{completion_date}} to {{expiry_date}}</p>
                    <p style="margin: 5px 0;"><strong>Amount Paid:</strong> ${{total_amount}}</p>
                    <p style="margin: 5px 0;"><strong>Status:</strong> <span style="color: #F59E0B; font-weight: bold;">Expired</span></p>
                </div>
                
                <h4 style="color: #374151; margin: 20px 0 15px 0;">What Happens Next:</h4>
                <div style="background-color: #fff7ed; border-left: 4px solid #F59E0B; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
                    <ul style="margin: 0; padding-left: 20px; color: #6b7280; line-height: 1.6;">
                        <li style="margin: 8px 0;"><strong>Removal Process:</strong> You will be removed as an authorized user within 3-5 business days</li>
                        <li style="margin: 8px 0;"><strong>Credit Report Impact:</strong> The tradeline may continue to appear on your credit report for some time after removal</li>
                        <li style="margin: 8px 0;"><strong>Score Changes:</strong> Your credit score may be affected once the tradeline is removed</li>
                        <li style="margin: 8px 0;"><strong>New Tradelines:</strong> Browse our marketplace for additional tradeline opportunities</li>
                    </ul>
                </div>
                
                <h4 style="color: #374151; margin: 20px 0 15px 0;">Service Review:</h4>
                <div style="background-color: #f0f9ff; border-left: 4px solid #0EA5E9; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
                    <p style="margin: 0 0 15px 0; color: #374151;">
                        We hope this tradeline helped improve your credit profile. Your feedback is valuable to us and helps improve our service.
                    </p>
                    <p style="margin: 0; color: #6b7280;">
                        <strong>Duration:</strong> {{service_duration}} days<br>
                        <strong>Investment:</strong> ${{total_amount}} for {{quantity}} spot(s)
                    </p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <div style="margin-bottom: 15px;">
                        <a href="https://rocket-app.tiberbuhealth.com/app" 
                           style="background-color: #17B26A; color: white; padding: 12px 24px; text-decoration: none; 
                                  border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block; margin-right: 10px;">
                            Browse New Tradelines
                        </a>
                    </div>
                    <div>
                        <a href="https://rocket-app.tiberbuhealth.com/support" 
                           style="background-color: #6b7280; color: white; padding: 10px 20px; text-decoration: none; 
                                  border-radius: 6px; font-weight: 500; font-size: 14px; display: inline-block;">
                            Contact Support
                        </a>
                    </div>
                </div>
                
                <p style="color: #6b7280; margin: 25px 0 0 0; font-size: 16px;">
                    Thank you for choosing RocketTradeline. We look forward to serving you again in the future!
                </p>
            """,
            "parameters": [
                {"parameter_name": "customer_name", "parameter_label": "Customer Name", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "tradeline_id", "parameter_label": "Tradeline ID", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "bank_name", "parameter_label": "Bank Name", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "credit_limit", "parameter_label": "Credit Limit", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "age_year", "parameter_label": "Age Year", "parameter_type": "Int", "is_required": 1},
                {"parameter_name": "age_month", "parameter_label": "Age Month", "parameter_type": "Int", "is_required": 1},
                {"parameter_name": "completion_date", "parameter_label": "Completion Date", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "expiry_date", "parameter_label": "Expiry Date", "parameter_type": "Date", "is_required": 1},
                {"parameter_name": "total_amount", "parameter_label": "Total Amount", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "service_duration", "parameter_label": "Service Duration", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "quantity", "parameter_label": "Quantity", "parameter_type": "Int", "is_required": 1}
            ]
        },
        {
            "template_name": "Refund Request Notification",
            "subject": "🔄 Refund Request - Client Tradeline {{client_tradeline_id}}",
            "description": "Admin notification email for refund requests",
            "template_type": "Notification",
            "html_content": """
                <h3 style="color: #DC2626; margin: 0 0 20px 0;">🔄 New Refund Request</h3>
                <p style="color: #374151; font-size: 16px; margin: 0 0 10px 0;">Dear Admin,</p>
                
                <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0 0 25px 0;">
                    A customer has requested a refund for their client tradeline. Please review the details below and take appropriate action.
                </p>
                
                <h4 style="color: #374151; margin: 20px 0 15px 0;">Refund Request Details:</h4>
                <div style="background-color: #fef2f2; border-left: 4px solid #DC2626; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
                    <p style="margin: 5px 0;"><strong>Client Tradeline ID:</strong> {{client_tradeline_id}}</p>
                    <p style="margin: 5px 0;"><strong>Request Date:</strong> {{request_date}}</p>
                    <p style="margin: 5px 0;"><strong>Requested By:</strong> {{requesting_user}}</p>
                    <p style="margin: 5px 0;"><strong>Previous Status:</strong> {{previous_status}}</p>
                    <p style="margin: 5px 0;"><strong>Current Status:</strong> <span style="color: #DC2626; font-weight: bold;">Refund Requested</span></p>
                    <p style="margin: 5px 0;"><strong>Refund Reason:</strong> {{refund_reason}}</p>
                </div>
                
                <h4 style="color: #374151; margin: 20px 0 15px 0;">Customer Information:</h4>
                <div style="background-color: #f9fafb; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
                    <p style="margin: 5px 0;"><strong>Customer ID:</strong> {{customer_id}}</p>
                    <p style="margin: 5px 0;"><strong>Customer Name:</strong> {{customer_name}}</p>
                    <p style="margin: 5px 0;"><strong>Customer Email:</strong> {{customer_email}}</p>
                    <p style="margin: 5px 0;"><strong>Customer Phone:</strong> {{customer_phone}}</p>
                </div>
                
                <h4 style="color: #374151; margin: 20px 0 15px 0;">Tradeline Information:</h4>
                <div style="background-color: #f0f9ff; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
                    <p style="margin: 5px 0;"><strong>Tradeline ID:</strong> {{tradeline_id}}</p>
                    <p style="margin: 5px 0;"><strong>Tradeline Name:</strong> {{tradeline_name}}</p>
                    <p style="margin: 5px 0;"><strong>Bank:</strong> {{bank_name}}</p>
                    <p style="margin: 5px 0;"><strong>Credit Limit:</strong> ${{credit_limit}}</p>
                    <p style="margin: 5px 0;"><strong>Age:</strong> {{tradeline_age}}</p>
                    <p style="margin: 5px 0;"><strong>Quantity Purchased:</strong> {{quantity}}</p>
                </div>
                
                <h4 style="color: #374151; margin: 20px 0 15px 0;">Financial Information:</h4>
                <div style="background-color: #fff7ed; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
                    <p style="margin: 5px 0;"><strong>Unit Price:</strong> ${{unit_price}}</p>
                    <p style="margin: 5px 0;"><strong>Total Amount Paid:</strong> <span style="font-size: 18px; font-weight: bold; color: #DC2626;">${{total_amount}}</span></p>
                    <p style="margin: 5px 0;"><strong>Payment Request ID:</strong> {{payment_request_id}}</p>
                    <p style="margin: 5px 0;"><strong>Cart ID:</strong> {{cart_id}}</p>
                </div>
                
                <h4 style="color: #374151; margin: 20px 0 15px 0;">Timeline Information:</h4>
                <div style="background-color: #f3f4f6; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
                    <p style="margin: 5px 0;"><strong>Purchase Date:</strong> {{purchase_date}}</p>
                    <p style="margin: 5px 0;"><strong>Completion Date:</strong> {{completion_date}}</p>
                    <p style="margin: 5px 0;"><strong>Expiry Date:</strong> {{expiry_date}}</p>
                    <p style="margin: 5px 0;"><strong>Last Modified:</strong> {{last_modified}}</p>
                </div>
                
                <h4 style="color: #374151; margin: 20px 0 15px 0;">Required Actions:</h4>
                <div style="background-color: #fef3c7; border-left: 4px solid #F59E0B; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
                    <ol style="margin: 0; padding-left: 20px; color: #6b7280; line-height: 1.6;">
                        <li style="margin: 8px 0;"><strong>Review the refund request</strong> and validate the reason</li>
                        <li style="margin: 8px 0;"><strong>Check payment records</strong> and transaction history</li>
                        <li style="margin: 8px 0;"><strong>Verify tradeline removal</strong> if applicable</li>
                        <li style="margin: 8px 0;"><strong>Process refund</strong> through appropriate payment method</li>
                        <li style="margin: 8px 0;"><strong>Update tradeline status</strong> to "Refunded" once processed</li>
                        <li style="margin: 8px 0;"><strong>Notify customer</strong> of refund processing status</li>
                    </ol>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://rocket-app.tiberbuhealth.com/app/client-tradelines/{{client_tradeline_id}}" 
                       style="background-color: #DC2626; color: white; padding: 14px 28px; text-decoration: none; 
                              border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block; margin-right: 10px;">
                        Review Tradeline
                    </a>
                    <a href="https://rocket-app.tiberbuhealth.com/app/customer/{{customer_id}}" 
                       style="background-color: #6b7280; color: white; padding: 14px 28px; text-decoration: none; 
                              border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">
                        View Customer
                    </a>
                </div>
                
                <div style="background-color: #fef2f2; border: 1px solid #fecaca; padding: 15px; border-radius: 6px; margin: 25px 0;">
                    <p style="margin: 0; color: #DC2626; font-weight: 600; font-size: 14px;">
                        ⚠️ Priority: Please process this refund request within 2-3 business days to maintain customer satisfaction.
                    </p>
                </div>
                
                <p style="color: #6b7280; margin: 25px 0 0 0; font-size: 16px;">
                    This is an automated notification from the RocketTradeline refund system.
                </p>
            """,
            "parameters": [
                {"parameter_name": "client_tradeline_id", "parameter_label": "Client Tradeline ID", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "request_date", "parameter_label": "Request Date", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "requesting_user", "parameter_label": "Requesting User", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "previous_status", "parameter_label": "Previous Status", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "refund_reason", "parameter_label": "Refund Reason", "parameter_type": "Text", "is_required": 0},
                {"parameter_name": "customer_id", "parameter_label": "Customer ID", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "customer_name", "parameter_label": "Customer Name", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "customer_email", "parameter_label": "Customer Email", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "customer_phone", "parameter_label": "Customer Phone", "parameter_type": "Data", "is_required": 0},
                {"parameter_name": "tradeline_id", "parameter_label": "Tradeline ID", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "tradeline_name", "parameter_label": "Tradeline Name", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "bank_name", "parameter_label": "Bank Name", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "credit_limit", "parameter_label": "Credit Limit", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "tradeline_age", "parameter_label": "Tradeline Age", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "quantity", "parameter_label": "Quantity", "parameter_type": "Int", "is_required": 1},
                {"parameter_name": "unit_price", "parameter_label": "Unit Price", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "total_amount", "parameter_label": "Total Amount", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "payment_request_id", "parameter_label": "Payment Request ID", "parameter_type": "Data", "is_required": 0},
                {"parameter_name": "cart_id", "parameter_label": "Cart ID", "parameter_type": "Data", "is_required": 0},
                {"parameter_name": "purchase_date", "parameter_label": "Purchase Date", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "completion_date", "parameter_label": "Completion Date", "parameter_type": "Data", "is_required": 0},
                {"parameter_name": "expiry_date", "parameter_label": "Expiry Date", "parameter_type": "Data", "is_required": 0},
                {"parameter_name": "last_modified", "parameter_label": "Last Modified", "parameter_type": "Data", "is_required": 1}
            ]
        },
        {
            "template_name": "Payment Approval",
            "subject": "Payment Approved - Your Tradelines Are Active!",
            "description": "Payment approval notification email template",
            "template_type": "Notification",
            "html_content": """
                <div style="margin-bottom: 25px;">
                    <h3 style="color: #17B26A; margin: 0 0 20px 0;">Payment Approved - Tradelines Activated!</h3>
                    <p style="color: #374151; font-size: 16px; margin: 0 0 10px 0;">Dear {{customer_name}},</p>
                    
                    <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0 0 25px 0;">
                        Great news! Your payment request has been approved and your tradelines are now active in your portal.
                    </p>
                </div>
                
                <!-- Payment Details -->
                <h4 style="color: #374151; margin: 20px 0 15px 0;">Payment Details:</h4>
                <div style="background-color: #f9fafb; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
                    <p style="margin: 5px 0;"><strong>Payment Request ID:</strong> {{payment_request_id}}</p>
                    <p style="margin: 5px 0;"><strong>Payment Method:</strong> {{payment_method}}</p>
                    <p style="margin: 5px 0;"><strong>Total Amount Paid:</strong> ${{total_amount}}</p>
                    <p style="margin: 5px 0;"><strong>Transaction ID:</strong> {{transaction_id}}</p>
                    <p style="margin: 5px 0;"><strong>Approved At:</strong> {{approved_at}}</p>
                </div>
                
                <!-- Tradeline Details -->
                {{tradeline_details}}
                
                <!-- Next Steps -->
                <h4 style="color: #374151; margin: 20px 0 15px 0;">Next Steps:</h4>
                <ol style="margin: 0 0 25px 20px; padding: 0; color: #6b7280; line-height: 1.6;">
                    <li style="margin: 5px 0;">Log in to your portal to view your active tradelines</li>
                    <li style="margin: 5px 0;">Monitor your credit report for the new tradelines (typically appears within 30-60 days)</li>
                    <li style="margin: 5px 0;">Contact our support team if you have any questions</li>
                </ol>
                
                <!-- Portal Access Button -->
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{{portal_link}}" 
                       style="background-color: #17B26A; color: white; padding: 12px 24px; text-decoration: none; 
                              border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">
                        Access Your Portal
                    </a>
                </div>
                
                <div style="margin-top: 25px;">
                    <p style="color: #6b7280; margin: 25px 0 0 0; font-size: 16px;">
                        Thank you for choosing RocketTradeline!
                    </p>
                </div>
                
                <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 25px 0;">
                <p style="font-size: 12px; color: #9ca3af; margin: 0;">
                    If you have any questions, please contact us at info@rockettradeline.com
                </p>
            """,
            "parameters": [
                {"parameter_name": "customer_name", "parameter_label": "Customer Name", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "payment_request_id", "parameter_label": "Payment Request ID", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "payment_method", "parameter_label": "Payment Method", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "total_amount", "parameter_label": "Total Amount", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "transaction_id", "parameter_label": "Transaction ID", "parameter_type": "Data", "is_required": 0},
                {"parameter_name": "approved_at", "parameter_label": "Approved At", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "tradeline_details", "parameter_label": "Tradeline Details", "parameter_type": "Text", "is_required": 0},
                {"parameter_name": "portal_link", "parameter_label": "Portal Link", "parameter_type": "Data", "is_required": 1}
            ]
        },
        {
            "template_name": "AU Assignment Notification",
            "subject": "New Authorized User Assigned to Your Tradeline - Action Required",
            "description": "Notification to cardholder when a new Authorized User is assigned to their tradeline",
            "template_type": "Notification",
            "html_content": """
                <div style="margin-bottom: 25px;">
                    <p style="color: #374151; font-size: 16px; margin: 0 0 10px 0;">Dear {{cardholder_first_name}},</p>
                    <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0;">
                        A new Authorized User (AU) has been assigned to your tradeline. Please review the details below:
                    </p>
                </div>
                
                <h4 style="color: #374151; margin: 20px 0 15px 0;">Authorized User Information:</h4>
                <div style="background-color: #f0f9ff; border-left: 4px solid #0EA5E9; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
                    <p style="margin: 5px 0;"><strong>Authorized User:</strong> {{au_first_name}} {{au_last_initial}}.</p>
                    <p style="margin: 5px 0;"><strong>Date of Birth:</strong> {{au_dob}}</p>
                    <p style="margin: 5px 0;"><strong>SSN (Last 4):</strong> {{au_ssn_last_4}}</p>
                </div>
                
                <h4 style="color: #374151; margin: 20px 0 15px 0;">Tradeline Information:</h4>
                <div style="background-color: #f9fafb; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
                    <p style="margin: 5px 0;"><strong>Year Opened:</strong> {{year_opened}}</p>
                    <p style="margin: 5px 0;"><strong>Bank:</strong> {{bank_name}}</p>
                    <p style="margin: 5px 0;"><strong>Credit Limit:</strong> ${{credit_limit}}</p>
                    <p style="margin: 5px 0;"><strong>Closing Statement Date:</strong> {{closing_date}}</p>
                    <p style="margin: 5px 0;"><strong>Your Payment Amount:</strong> <span style="font-size: 18px; font-weight: bold; color: #059669;">${{payment_amount}}</span></p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{{cardholder_login_link}}" style="background-color: #0EA5E9; color: white; padding: 14px 28px; text-decoration: none; 
                              border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">
                        Access Cardholder Account
                    </a>
                </div>
                
                <h4 style="color: #374151; margin: 20px 0 15px 0;">Next Steps:</h4>
                <div style="background-color: #fef3c7; border-left: 4px solid #F59E0B; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
                    <ol style="margin: 0; padding-left: 20px; color: #6b7280; line-height: 1.6;">
                        <li style="margin: 8px 0;"><strong>Add the Authorized User</strong> to your tradeline within 24 hours.</li>
                        <li style="margin: 8px 0;"><strong>Upload screenshots</strong> confirming the AU has been successfully added to the Cardholder Portal.</li>
                        <li style="margin: 8px 0;"><strong>Payment release:</strong> Once your confirmation is reviewed and approved, payment will be released to your preferred method of payment.</li>
                    </ol>
                </div>
                
                <div style="background-color: #d1fae5; border: 1px solid #6ee7b7; padding: 15px; border-radius: 6px; margin: 25px 0;">
                    <p style="margin: 0; color: #059669; font-weight: 600; font-size: 14px;">
                        💡 Remember: Prompt action ensures faster payment processing and helps maintain your excellent seller rating.
                    </p>
                </div>
                
                <p style="color: #6b7280; margin: 25px 0 0 0; font-size: 16px; line-height: 1.6;">
                    Thank you for your prompt attention to this matter.<br><br>
                    Best regards,<br>
                    <strong>Rocket Tradeline Team</strong>
                </p>
            """,
            "parameters": [
                {"parameter_name": "cardholder_first_name", "parameter_label": "Cardholder First Name", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "au_first_name", "parameter_label": "AU First Name", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "au_last_initial", "parameter_label": "AU Last Initial", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "au_dob", "parameter_label": "AU Date of Birth", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "au_ssn_last_4", "parameter_label": "AU SSN Last 4", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "year_opened", "parameter_label": "Year Opened", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "bank_name", "parameter_label": "Bank Name", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "credit_limit", "parameter_label": "Credit Limit", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "closing_date", "parameter_label": "Closing Date", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "payment_amount", "parameter_label": "Payment Amount", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "cardholder_login_link", "parameter_label": "Cardholder Login Link", "parameter_type": "Data", "is_required": 1}
            ]
        },
        {
            "template_name": "Payment Request Notification",
            "subject": "New Payment Request - {{payment_request_id}}",
            "description": "Notification to admin when a new payment request is created",
            "template_type": "Notification",
            "html_content": """
                <div style="margin-bottom: 25px;">
                    <h3 style="color: #374151; margin: 0 0 20px 0;">New Payment Request Created</h3>
                    <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0;">
                        A new payment request has been submitted and requires your review.
                    </p>
                </div>
                
                <h4 style="color: #374151; margin: 20px 0 15px 0;">Payment Request Details:</h4>
                <div style="background-color: #f9fafb; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
                    <p style="margin: 5px 0;"><strong>Payment Request ID:</strong> {{payment_request_id}}</p>
                    <p style="margin: 5px 0;"><strong>Customer:</strong> {{customer_name}} ({{customer_email}})</p>
                    <p style="margin: 5px 0;"><strong>Payment Method:</strong> {{payment_method}}</p>
                    <p style="margin: 5px 0;"><strong>Amount:</strong> ${{amount}}</p>
                    <p style="margin: 5px 0;"><strong>Total Amount:</strong> <span style="font-size: 18px; font-weight: bold; color: #059669;">${{total_amount}}</span></p>
                    <p style="margin: 5px 0;"><strong>Cart ID:</strong> {{cart_id}}</p>
                    <p style="margin: 5px 0;"><strong>Status:</strong> <span style="color: #F59E0B; font-weight: bold;">{{status}}</span></p>
                    <p style="margin: 5px 0;"><strong>Created At:</strong> {{created_at}}</p>
                </div>
                
                <h4 style="color: #374151; margin: 20px 0 15px 0;">Action Required:</h4>
                <div style="background-color: #fef3c7; border-left: 4px solid #F59E0B; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
                    <p style="color: #6b7280; line-height: 1.6; margin: 0 0 20px 0;">
                        Please log in to the admin portal to review and approve this payment request.
                    </p>
                    <ul style="margin: 0; padding-left: 20px; color: #6b7280; line-height: 1.6;">
                        <li style="margin: 8px 0;">Review payment request details and customer information</li>
                        <li style="margin: 8px 0;">Verify payment method and amount</li>
                        <li style="margin: 8px 0;">Check cart contents for accuracy</li>
                        <li style="margin: 8px 0;">Approve or reject the payment request</li>
                    </ul>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{{payment_request_url}}" 
                       style="background-color: #17B26A; color: white; padding: 14px 28px; text-decoration: none; 
                              border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block; margin-right: 10px;">
                        View Payment Request
                    </a>
                    <a href="{{admin_portal_url}}" 
                       style="background-color: #6b7280; color: white; padding: 14px 28px; text-decoration: none; 
                              border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">
                        Admin Portal
                    </a>
                </div>
                
                <div style="background-color: #d1fae5; border: 1px solid #6ee7b7; padding: 15px; border-radius: 6px; margin: 25px 0;">
                    <p style="margin: 0; color: #059669; font-weight: 600; font-size: 14px;">
                        💡 Tip: Quick approval helps maintain customer satisfaction and ensures smooth transaction processing.
                    </p>
                </div>
                
                <p style="color: #6b7280; margin: 25px 0 0 0; font-size: 16px; line-height: 1.6;">
                    This is an automated notification from the RocketTradeline payment system.<br>
                    For assistance, contact the development team.
                </p>
            """,
            "parameters": [
                {"parameter_name": "payment_request_id", "parameter_label": "Payment Request ID", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "customer_name", "parameter_label": "Customer Name", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "customer_email", "parameter_label": "Customer Email", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "payment_method", "parameter_label": "Payment Method", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "amount", "parameter_label": "Amount", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "total_amount", "parameter_label": "Total Amount", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "cart_id", "parameter_label": "Cart ID", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "status", "parameter_label": "Status", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "created_at", "parameter_label": "Created At", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "payment_request_url", "parameter_label": "Payment Request URL", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "admin_portal_url", "parameter_label": "Admin Portal URL", "parameter_type": "Data", "is_required": 0}
            ]
        },
        {
            "template_name": "Active Status Notification",
            "subject": "Authorized User Added - Next Steps for Your Order - {{customer_name}}",
            "description": "Notification to customer when their tradeline status changes to Active",
            "template_type": "Notification",
            "html_content": """
                <div style="margin-bottom: 25px;">
                    <p style="color: #374151; font-size: 16px; margin: 0 0 15px 0;">
                        Thank you for your tradeline order. The Authorized User (AU) below was successfully added! Attached is your confirmation for reference.
                    </p>
                    <p style="color: #DC2626; font-weight: bold; font-size: 16px; margin: 0;">
                        <strong>Note:</strong> To finalize your order, you must follow the instructions below.
                    </p>
                </div>
                
                <h4 style="color: #374151; margin: 20px 0 15px 0;">AU Information:</h4>
                <div style="background-color: #f0f9ff; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
                    <p style="margin: 5px 0;"><strong>AU:</strong> {{au_name}}</p>
                </div>
                
                <h4 style="color: #374151; margin: 20px 0 15px 0;">Tradeline(s):</h4>
                <div style="background-color: #f9fafb; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
                    <p style="margin: 5px 0;">{{tradeline_info}}</p>
                </div>
                
                <div style="background-color: #fef3c7; border-left: 4px solid #F59E0B; padding: 20px; border-radius: 6px; margin: 25px 0;">
                    <h4 style="color: #92400e; margin: 0 0 15px 0;">⚠️ IMPORTANT NEXT STEPS:</h4>
                    <p style="color: #6b7280; line-height: 1.6; margin: 0 0 15px 0;">
                        To help ensure your tradeline posts correctly to your credit report, you must create an account with a credit reporting site immediately. Then, add the following mailing address exactly as it appears to your list of known addresses:
                    </p>
                    <div style="background-color: #f3f4f6; padding: 15px; border-radius: 6px; margin: 15px 0;">
                        <p style="margin: 0; font-family: monospace; font-weight: bold; color: #374151;">
                            📍 {{mailing_address}}
                        </p>
                    </div>
                    <p style="color: #DC2626; font-weight: bold; margin: 15px 0 0 0;">
                        If this step is not completed, the tradeline will not post to your credit report, and you will not be eligible for a refund.
                    </p>
                    <p style="color: #6b7280; margin: 15px 0 0 0;">
                        You can use any of the following sites to complete this step:<br>
                        <strong>Try Smart Credit, IdentityIQ, Experian, Free Score Fast, Identity Guard, LifeLock, Credit Karma</strong>
                    </p>
                </div>
                
                <h4 style="color: #374151; margin: 30px 0 15px 0;">Important Tradeline Information</h4>
                <div style="background-color: #f9fafb; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
                    <ul style="margin: 0; padding-left: 20px; color: #6b7280; line-height: 1.6;">
                        <li style="margin: 8px 0;"><strong>Cycle Skips:</strong> Tradelines may skip cycles. Once your information is entered into the system, it is up to the creditors and credit bureaus to report the tradeline on your credit report.</li>
                        <li style="margin: 8px 0;"><strong>Refund Policy:</strong> If your tradeline does not report after the 7th day of the second billing cycle, you are eligible for a full refund.</li>
                        <li style="margin: 8px 0;"><strong>Reporting Time:</strong> Tradelines typically take 7-14 days from the statement date to appear on your credit report. Purchase at least 8 days before the statement date to avoid cycle skips.</li>
                        <li style="margin: 8px 0;"><strong>Reporting Bureaus:</strong> Tradelines generally report to all three major bureaus (Experian, Equifax, and TransUnion), but we only guarantee reporting to at least one.</li>
                        <li style="margin: 8px 0;"><strong>Proof of AU Status:</strong> Provided when available. Not all screenshot requests can be fulfilled.</li>
                        <li style="margin: 8px 0;"><strong>No Physical Card:</strong> This method is for credit enhancement only; you will not receive a physical credit card.</li>
                        <li style="margin: 8px 0;"><strong>Refunds & Restrictions:</strong> If a card requires documentation, you must provide it, or you will not be eligible for a refund. If a card is shut down but has already reported, you may receive half a refund, but no replacements.</li>
                        <li style="margin: 8px 0;"><strong>AMEX Note:</strong> AMEX tradelines will reflect the year the AU was added, not the year the card was opened.</li>
                    </ul>
                </div>
                
                <div style="background-color: #fef2f2; border-left: 4px solid #DC2626; padding: 20px; border-radius: 6px; margin: 25px 0;">
                    <h4 style="color: #DC2626; margin: 0 0 15px 0;">⚠️ By purchasing, you agree to the following:</h4>
                    <ul style="margin: 0; padding-left: 20px; color: #6b7280; line-height: 1.6;">
                        <li style="margin: 8px 0;">If you attempt anything that violates our agreement, you will be removed immediately.</li>
                        <li style="margin: 8px 0;">A collection may be reported to all three bureaus for the full tradeline amount if any terms are violated.</li>
                    </ul>
                </div>
                
                <p style="color: #6b7280; margin: 25px 0 0 0; font-size: 16px; line-height: 1.6;">
                    We look forward to assisting you with your credit-building journey. If you have any questions, feel free to reply to this email.<br><br>
                    <strong>Best regards,<br>
                    Rocket Tradeline Team</strong>
                </p>
            """,
            "parameters": [
                {"parameter_name": "customer_name", "parameter_label": "Customer Name", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "customer_first_name", "parameter_label": "Customer First Name", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "customer_last_name", "parameter_label": "Customer Last Name", "parameter_type": "Data", "is_required": 0},
                {"parameter_name": "au_name", "parameter_label": "AU Name", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "year_opened", "parameter_label": "Year Opened", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "bank_name", "parameter_label": "Bank Name", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "credit_limit_k", "parameter_label": "Credit Limit (K format)", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "closing_day", "parameter_label": "Closing Day", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "tradeline_info", "parameter_label": "Tradeline Info", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "mailing_address", "parameter_label": "Mailing Address", "parameter_type": "Data", "is_required": 1}
            ]
        },
        {
            "template_name": "Removal Confirmation",
            "subject": "Authorized User Removal Confirmation",
            "description": "Confirmation email to customer when their tradeline status changes to Removed",
            "template_type": "Notification",
            "html_content": """
                <div style="margin-bottom: 25px;">
                    <p style="color: #374151; font-size: 16px; margin: 0 0 15px 0;">Dear {{au_name}},</p>
                    <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0 0 20px 0;">
                        We are writing to confirm that your 60-day term as an authorized user on the following tradeline has ended, and your removal from the account has been completed:
                    </p>
                </div>
                
                <h4 style="color: #374151; margin: 20px 0 15px 0;">Tradeline Information:</h4>
                <div style="background-color: #f0f9ff; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
                    <p style="margin: 5px 0;"><strong>Tradeline:</strong> {{tradeline_info}}</p>
                    <p style="margin: 5px 0;"><strong>Authorized User:</strong> {{customer_name}}</p>
                </div>
                
                <div style="background-color: #fef3c7; border-left: 4px solid #F59E0B; padding: 20px; border-radius: 6px; margin: 25px 0;">
                    <p style="color: #6b7280; line-height: 1.6; margin: 0 0 15px 0;">
                        At this time, please ensure that you <strong>update your credit profile to remove the cardholder's address</strong> you added when this tradeline was established. This helps maintain accurate records and prevents potential confusion on future credit applications. 
                    </p>
                    <p style="color: #6b7280; line-height: 1.6; margin: 0;">
                        Otherwise, no further action is required.
                    </p>
                </div>
                
                <p style="color: #6b7280; margin: 25px 0 0 0; font-size: 16px; line-height: 1.6;">
                    Thank you for working with us. We appreciate your cooperation and trust in our process.<br><br>
                    <strong>Best regards,<br>
                    Rocket Tradeline Team</strong>
                </p>
            """,
            "parameters": [
                {"parameter_name": "customer_name", "parameter_label": "Customer Name", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "au_name", "parameter_label": "AU Name", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "bank_name", "parameter_label": "Bank Name", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "year_opened", "parameter_label": "Year Opened", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "credit_limit", "parameter_label": "Credit Limit", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "tradeline_info", "parameter_label": "Tradeline Info", "parameter_type": "Data", "is_required": 1}
            ]
        },
        {
            "template_name": "Tradeline Closing Date Notification",
            "subject": "Tradeline Closing Date Reached - Important Information",
            "description": "Notification sent 2 days after the tradeline closing date passes to inform client",
            "template_type": "Notification",
            "html_content": """
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
            """,
            "parameters": [
                {"parameter_name": "customer_name", "parameter_label": "Customer Name", "parameter_type": "Data", "is_required": 1},
                {"parameter_name": "tradelines_html", "parameter_label": "Tradelines HTML", "parameter_type": "Text", "is_required": 1},
                {"parameter_name": "tradelines_count", "parameter_label": "Number of Tradelines", "parameter_type": "Data", "is_required": 0},
                {"parameter_name": "client_email", "parameter_label": "Client Email", "parameter_type": "Data", "is_required": 1}
            ]
        }
    ]
    
    created_templates = []
    updated_templates = []
    errors = []
    
    for template_data in templates:
        try:
            template_name = template_data["template_name"]
            
            # Check if template already exists
            if frappe.db.exists("Email Template Custom", template_name):
                print(f"Template '{template_name}' already exists, skipping update...")
                
                # # Update existing template
                # existing_template = frappe.get_doc("Email Template Custom", template_name)
                # 
                # # Update main fields
                # existing_template.subject = template_data["subject"]
                # existing_template.description = template_data["description"]
                # existing_template.template_type = template_data["template_type"]
                # existing_template.html_content = template_data["html_content"]
                # existing_template.is_active = 1
                # 
                # # Clear existing parameters
                # existing_template.parameters = []
                # 
                # # Add new parameters
                # for param in template_data.get("parameters", []):
                #     existing_template.append("parameters", param)
                # 
                # existing_template.save(ignore_permissions=True)
                # updated_templates.append(template_name)
                
            else:
                print(f"Creating new template: {template_name}")
                
                # Extract parameters for separate handling
                parameters = template_data.pop("parameters", [])
                
                # Create new template document
                template = frappe.get_doc({
                    "doctype": "Email Template Custom",
                    "is_active": 1,
                    **template_data
                })
                
                # Add parameters as child table rows
                for param in parameters:
                    template.append("parameters", param)
                
                # Insert the template
                template.insert(ignore_permissions=True)
                created_templates.append(template_name)
                
            frappe.db.commit()
            print(f"✅ Successfully processed template: {template_name}")
            
        except Exception as e:
            error_msg = f"❌ Error processing template {template_data.get('template_name', 'Unknown')}: {str(e)}"
            print(error_msg)
            errors.append(error_msg)
            frappe.log_error(error_msg, "Email Template Generator")
    
    # Print summary
    print("\n" + "="*60)
    print("EMAIL TEMPLATE GENERATION SUMMARY")
    print("="*60)
    
    if created_templates:
        print(f"✅ CREATED ({len(created_templates)} templates):")
        for template in created_templates:
            print(f"   - {template}")
    
    if updated_templates:
        print(f"🔄 UPDATED ({len(updated_templates)} templates):")
        for template in updated_templates:
            print(f"   - {template}")
    
    if errors:
        print(f"❌ ERRORS ({len(errors)} errors):")
        for error in errors:
            print(f"   - {error}")
    
    total_processed = len(created_templates) + len(updated_templates)
    print(f"\n📊 TOTAL PROCESSED: {total_processed} templates")
    print(f"🎯 SUCCESS RATE: {((total_processed)/(total_processed + len(errors))*100):.1f}%" if (total_processed + len(errors)) > 0 else "100%")
    
    return {
        "created": created_templates,
        "updated": updated_templates,
        "errors": errors,
        "total_processed": total_processed
    }


def delete_all_email_templates():
    """
    Delete all existing email templates (use with caution)
    """
    try:
        templates = frappe.get_all("Email Template Custom", fields=["name"])
        
        for template in templates:
            frappe.delete_doc("Email Template Custom", template.name, ignore_permissions=True)
        
        frappe.db.commit()
        print(f"✅ Deleted {len(templates)} email templates")
        
        return {"deleted": len(templates)}
        
    except Exception as e:
        error_msg = f"❌ Error deleting email templates: {str(e)}"
        print(error_msg)
        frappe.log_error(error_msg, "Email Template Deletion")
        return {"error": error_msg}


def reset_email_templates():
    """
    Delete all existing templates and recreate them from scratch
    """
    print("🔄 Resetting all email templates...")
    
    # Delete existing templates
    delete_result = delete_all_email_templates()
    
    # Create new templates
    create_result = generate_email_templates()
    
    print("\n" + "="*60)
    print("EMAIL TEMPLATE RESET COMPLETE")
    print("="*60)
    
    return {
        "deleted": delete_result.get("deleted", 0),
        "created": len(create_result.get("created", [])),
        "errors": create_result.get("errors", [])
    }


def execute():
    """
    Main execution function for bench execute command
    """
    print("🚀 Starting Email Template Generator for RocketTradeline...")
    print("="*60)
    
    # Check if DocTypes exist
    if not frappe.db.exists("DocType", "Email Template Custom"):
        print("❌ Email Template Custom DocType not found!")
        print("Please ensure the DocType is installed first.")
        return
        
    if not frappe.db.exists("DocType", "Email Template Parameter"):
        print("❌ Email Template Parameter DocType not found!")
        print("Please ensure the DocType is installed first.")
        return
    
    # Generate templates
    result = generate_email_templates()
    
    print("\n🎉 Email Template Generation Complete!")
    
    return result


if __name__ == "__main__":
    execute()
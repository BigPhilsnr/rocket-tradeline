import frappe
from frappe import _
from frappe.utils import validate_email_address, now_datetime
from .utils import is_administrator
from .auth import jwt_required, get_authenticated_user, get_email_header, get_email_footer
from rockettradeline.utils.email_templates import send_email_from_template

# Email Group Management APIs

@frappe.whitelist(allow_guest=True)
def subscribe_to_newsletter(email, full_name=None):
    """
    Add user to Website Subscribers email group
    Allows guest access for newsletter subscriptions
    """
    try:
        # Validate email format
        if not email or not validate_email_address(email):
            return {
                "success": False,
                "message": "Please provide a valid email address"
            }
        
        # Check if Website Subscribers email group exists, create if not
        email_group_name = "Website Subscribers"
        if not frappe.db.exists("Email Group", email_group_name):
            # Create the email group
            email_group = frappe.get_doc({
                "doctype": "Email Group",
                "title": email_group_name,
                "description": "Subscribers to RocketTradeline website newsletter and updates"
            })
            email_group.insert(ignore_permissions=True)
            frappe.db.commit()
        
        # Check if email is already subscribed
        existing_member = frappe.db.exists("Email Group Member", {
            "email_group": email_group_name,
            "email": email
        })
        
        if existing_member:
            # Check if they're unsubscribed and resubscribe them
            member_doc = frappe.get_doc("Email Group Member", existing_member)
            if member_doc.unsubscribed:
                member_doc.unsubscribed = 0
                member_doc.save(ignore_permissions=True)
                frappe.db.commit()
                
                # Send welcome email for resubscribed user
                try:
                    send_newsletter_welcome_email(email, full_name)
                except Exception as e:
                    # Log error but don't fail the subscription
                    frappe.log_error(f"Failed to send welcome email to resubscribed user {email}: {str(e)}", "Newsletter Welcome Email Error")
                
                return {
                    "success": True,
                    "message": "Successfully resubscribed to newsletter!",
                    "email": email,
                    "group": email_group_name,
                    "status": "resubscribed"
                }
            else:
                return {
                    "success": True,
                    "message": "Email is already subscribed to newsletter",
                    "email": email,
                    "group": email_group_name,
                    "status": "already_subscribed"
                }
        
        # Add new member to email group
        email_member = frappe.get_doc({
            "doctype": "Email Group Member",
            "email_group": email_group_name,
            "email": email,
            "unsubscribed": 0
        })
        email_member.insert(ignore_permissions=True)
        
        # If user exists, update their information
        if frappe.db.exists("User", email):
            try:
                user_doc = frappe.get_doc("User", email)
                if full_name and not user_doc.full_name:
                    user_doc.full_name = full_name
                    if full_name:
                        name_parts = full_name.split()
                        user_doc.first_name = name_parts[0] if name_parts else ""
                        user_doc.last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                    user_doc.save(ignore_permissions=True)
            except Exception as e:
                # Log error but don't fail the subscription
                frappe.log_error(f"Error updating user info for {email}: {str(e)}")
        
        frappe.db.commit()
        
        # Send welcome email to the new subscriber
        try:
            send_newsletter_welcome_email(email, full_name)
        except Exception as e:
            # Log error but don't fail the subscription
            frappe.log_error(f"Failed to send welcome email to {email}: {str(e)}", "Newsletter Welcome Email Error")
        
        return {
            "success": True,
            "message": "Successfully subscribed to newsletter!",
            "email": email,
            "group": email_group_name,
            "status": "subscribed",
            "full_name": full_name
        }
        
    except Exception as e:
        frappe.log_error(f"Newsletter subscription error: {str(e)}")
        return {
            "success": False,
            "message": f"Subscription failed: {str(e)}"
        }

def send_newsletter_welcome_email(email, full_name=None):
    """
    Send welcome email to new newsletter subscriber
    
    Args:
        email (str): Subscriber's email address
        full_name (str): Subscriber's full name (optional)
    """
    try:
        # Get consistent email header and footer
        email_header = get_email_header()
        email_footer = get_email_footer(email)
        
        # Prepare personalized greeting
        greeting_name = full_name if full_name else email.split('@')[0].title()
        
        # Create welcome email content
        subject = "Welcome to RocketTradeline Newsletter! 🚀"
        
        welcome_message = f"""{email_header}
        <h3 style="color: #17B26A; margin: 0 0 20px 0;">🎉 Welcome to RocketTradeline!</h3>
        <p style="color: #374151; font-size: 16px; margin: 0 0 10px 0;">Dear {greeting_name},</p>
        
        <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0 0 25px 0;">
            Thank you for subscribing to the RocketTradeline newsletter! We're excited to have you join our community of smart credit builders and tradeline enthusiasts.
        </p>
        
        <h4 style="color: #374151; margin: 20px 0 15px 0;">What You Can Expect:</h4>
        <div style="background-color: #f0f9ff; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
            <ul style="margin: 0; padding-left: 20px; color: #6b7280; line-height: 1.8;">
                <li style="margin: 8px 0;"><strong>Exclusive Tradeline Opportunities:</strong> Be the first to know about new tradelines and special offers</li>
                <li style="margin: 8px 0;"><strong>Credit Building Tips:</strong> Expert advice and strategies to improve your credit score</li>
                <li style="margin: 8px 0;"><strong>Industry Updates:</strong> Latest news and trends in the credit and tradeline industry</li>
                <li style="margin: 8px 0;"><strong>Educational Content:</strong> Guides, tutorials, and best practices for credit optimization</li>
                <li style="margin: 8px 0;"><strong>Special Promotions:</strong> Subscriber-only discounts and exclusive deals</li>
            </ul>
        </div>
        
        <h4 style="color: #374151; margin: 20px 0 15px 0;">Ready to Get Started?</h4>
        <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0 0 25px 0;">
            Explore our platform and discover how RocketTradeline can help you achieve your credit goals faster and more effectively.
        </p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="https://rockettradeline.com/tradelines" 
               style="background-color: #17B26A; color: white; padding: 14px 28px; text-decoration: none; 
                      border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block; margin-right: 10px;">
                Browse Tradelines
            </a>
            <a href="https://rockettradeline.com/credit-guide" 
               style="background-color: #6b7280; color: white; padding: 14px 28px; text-decoration: none; 
                      border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">
                Credit Guide
            </a>
        </div>
        
        <div style="background-color: #fef3c7; border-left: 4px solid #F59E0B; padding: 20px; border-radius: 6px; margin: 25px 0;">
            <h5 style="color: #92400e; margin: 0 0 10px 0; font-size: 16px;">💡 Pro Tip</h5>
            <p style="margin: 0; color: #92400e; font-size: 14px;">
                Follow us on social media for daily credit tips and real-time updates on new tradeline opportunities!
            </p>
        </div>
        
        <h4 style="color: #374151; margin: 20px 0 15px 0;">Need Help?</h4>
        <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0 0 25px 0;">
            Our support team is here to help you succeed. Feel free to reach out with any questions about tradelines, credit building, or our services.
        </p>
        
        <div style="background-color: #f9fafb; padding: 20px; border-radius: 6px; margin: 25px 0;">
            <h5 style="color: #374151; margin: 0 0 15px 0; font-size: 16px;">📞 Contact Information</h5>
            <p style="margin: 5px 0; color: #6b7280;"><strong>Email:</strong> info@rockettradeline.com</p>
            <p style="margin: 5px 0; color: #6b7280;"><strong>Support Hours:</strong> Monday - Friday, 9 AM - 6 PM EST</p>
            <p style="margin: 5px 0; color: #6b7280;"><strong>Response Time:</strong> Within 24 hours</p>
        </div>
        
        <p style="color: #6b7280; margin: 25px 0 0 0; font-size: 16px;">
            Welcome aboard, and thank you for choosing RocketTradeline for your credit building journey!
        </p>
        
        <p style="color: #374151; margin: 15px 0 0 0; font-size: 16px; font-weight: 600;">
            Best regards,<br>
            The RocketTradeline Team 🚀
        </p>
        
        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 25px 0;">
        <div style="text-align: center;">
            <p style="font-size: 12px; color: #9ca3af; margin: 0 0 10px 0;">
                You're receiving this email because you subscribed to RocketTradeline newsletter.
            </p>
            <p style="font-size: 12px; color: #9ca3af; margin: 0;">
                <a href="https://rockettradeline.com/unsubscribe?email={email}" style="color: #17B26A; text-decoration: none;">
                    Unsubscribe
                </a> | 
                <a href="https://rockettradeline.com/privacy" style="color: #17B26A; text-decoration: none;">
                    Privacy Policy
                </a>
            </p>
        </div>
        {email_footer}"""
        
        # Send welcome email
        frappe.sendmail(
            recipients=[email],
            subject=subject,
            message=welcome_message,
            header=["Welcome to RocketTradeline Newsletter", "green"],
            delayed=False  # Send immediately for welcome emails
        )
        
        # Log successful email send
        frappe.logger().info(f"Newsletter welcome email sent successfully to {email}")
        
        return True
        
    except Exception as e:
        frappe.log_error(f"Failed to send newsletter welcome email to {email}: {str(e)}", "Newsletter Welcome Email Error")
        return False

@frappe.whitelist(allow_guest=True)
def unsubscribe_from_newsletter(email, token=None):
    """
    Unsubscribe user from Website Subscribers email group
    Allows guest access for unsubscribe functionality
    """
    try:
        # Validate email format
        if not email or not validate_email_address(email):
            return {
                "success": False,
                "message": "Please provide a valid email address"
            }
        
        email_group_name = "Website Subscribers"
        
        # Find the email group member
        member = frappe.db.exists("Email Group Member", {
            "email_group": email_group_name,
            "email": email
        })
        
        if not member:
            return {
                "success": False,
                "message": "Email address is not subscribed to newsletter"
            }
        
        # Update member to unsubscribed
        member_doc = frappe.get_doc("Email Group Member", member)
        member_doc.unsubscribed = 1
        member_doc.save(ignore_permissions=True)
        frappe.db.commit()
        
        return {
            "success": True,
            "message": "Successfully unsubscribed from newsletter",
            "email": email,
            "group": email_group_name,
            "status": "unsubscribed"
        }
        
    except Exception as e:
        frappe.log_error(f"Newsletter unsubscribe error: {str(e)}")
        return {
            "success": False,
            "message": f"Unsubscribe failed: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def check_newsletter_subscription(email):
    """
    Check if email is subscribed to Website Subscribers
    Allows guest access for subscription status checking
    """
    try:
        # Validate email format
        if not email or not validate_email_address(email):
            return {
                "success": False,
                "message": "Please provide a valid email address"
            }
        
        email_group_name = "Website Subscribers"
        
        # Check if email group member exists
        member = frappe.db.get_value("Email Group Member", {
            "email_group": email_group_name,
            "email": email
        }, ["name", "unsubscribed"], as_dict=True)
        
        if not member:
            return {
                "success": True,
                "email": email,
                "subscribed": False,
                "status": "not_subscribed"
            }
        
        is_subscribed = not bool(member.unsubscribed)
        
        return {
            "success": True,
            "email": email,
            "subscribed": is_subscribed,
            "status": "subscribed" if is_subscribed else "unsubscribed"
        }
        
    except Exception as e:
        frappe.log_error(f"Newsletter subscription check error: {str(e)}")
        return {
            "success": False,
            "message": f"Subscription check failed: {str(e)}"
        }

@frappe.whitelist(allow_guest=False)
@jwt_required()
def get_newsletter_subscribers(limit=50, start=0):
    """
    Get list of newsletter subscribers (Admin only)
    Requires authentication
    """
    try:
        # Check if user has permission to view email groups
        user = get_authenticated_user()
        if not is_administrator(user):
            return {
                "success": False,
                "message": "Insufficient permissions to view subscribers"
            }
        
        email_group_name = "Website Subscribers"
        
        # Get subscribers with pagination
        subscribers = frappe.get_all("Email Group Member",
            filters={
                "email_group": email_group_name,
                "unsubscribed": 0
            },
            fields=["email", "creation", "modified"],
            order_by="creation desc",
            limit_start=start,
            limit_page_length=limit
        )
        
        # Get total count
        total_count = frappe.db.count("Email Group Member", {
            "email_group": email_group_name,
            "unsubscribed": 0
        })
        
        return {
            "success": True,
            "subscribers": subscribers,
            "total_count": total_count,
            "limit": limit,
            "start": start,
            "group": email_group_name
        }
        
    except Exception as e:
        frappe.log_error(f"Get newsletter subscribers error: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to get subscribers: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def subscribe_to_email_group(email, email_group, full_name=None):
    """
    Add user to any specified email group
    Allows guest access for flexible email group subscriptions
    """
    try:
        # Validate email format
        if not email or not validate_email_address(email):
            return {
                "success": False,
                "message": "Please provide a valid email address"
            }
        
        if not email_group:
            return {
                "success": False,
                "message": "Email group name is required"
            }
        
        # Check if email group exists
        if not frappe.db.exists("Email Group", email_group):
            return {
                "success": False,
                "message": f"Email group '{email_group}' does not exist"
            }
        
        # Check if email is already subscribed
        existing_member = frappe.db.exists("Email Group Member", {
            "email_group": email_group,
            "email": email
        })
        
        if existing_member:
            # Check if they're unsubscribed and resubscribe them
            member_doc = frappe.get_doc("Email Group Member", existing_member)
            if member_doc.unsubscribed:
                member_doc.unsubscribed = 0
                member_doc.save(ignore_permissions=True)
                frappe.db.commit()
                
                # Send welcome email if resubscribing to Website Subscribers group
                if email_group == "Website Subscribers":
                    try:
                        send_newsletter_welcome_email(email, full_name)
                    except Exception as e:
                        # Log error but don't fail the subscription
                        frappe.log_error(f"Failed to send welcome email to resubscribed user {email}: {str(e)}", "Newsletter Welcome Email Error")
                
                return {
                    "success": True,
                    "message": f"Successfully resubscribed to {email_group}!",
                    "email": email,
                    "group": email_group,
                    "status": "resubscribed"
                }
            else:
                return {
                    "success": True,
                    "message": f"Email is already subscribed to {email_group}",
                    "email": email,
                    "group": email_group,
                    "status": "already_subscribed"
                }
        
        # Add new member to email group
        email_member = frappe.get_doc({
            "doctype": "Email Group Member",
            "email_group": email_group,
            "email": email,
            "unsubscribed": 0
        })
        email_member.insert(ignore_permissions=True)
        
        # If user exists, update their information
        if frappe.db.exists("User", email):
            try:
                user_doc = frappe.get_doc("User", email)
                if full_name and not user_doc.full_name:
                    user_doc.full_name = full_name
                    if full_name:
                        name_parts = full_name.split()
                        user_doc.first_name = name_parts[0] if name_parts else ""
                        user_doc.last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
                    user_doc.save(ignore_permissions=True)
            except Exception as e:
                # Log error but don't fail the subscription
                frappe.log_error(f"Error updating user info for {email}: {str(e)}")
        
        frappe.db.commit()
        
        # Send welcome email if subscribing to Website Subscribers group
        if email_group == "Website Subscribers":
            try:
                send_newsletter_welcome_email(email, full_name)
            except Exception as e:
                # Log error but don't fail the subscription
                frappe.log_error(f"Failed to send welcome email to {email}: {str(e)}", "Newsletter Welcome Email Error")
        
        return {
            "success": True,
            "message": f"Successfully subscribed to {email_group}!",
            "email": email,
            "group": email_group,
            "status": "subscribed",
            "full_name": full_name
        }
        
    except Exception as e:
        frappe.log_error(f"Email group subscription error: {str(e)}")
        return {
            "success": False,
            "message": f"Subscription failed: {str(e)}"
        }

@frappe.whitelist()
def get_email_groups():
    """
    Get list of all email groups (Admin only)
    Requires authentication
    """
    try:
        # Check if user has permission to view email groups
        if not frappe.has_permission("Email Group", "read"):
            return {
                "success": False,
                "message": "Insufficient permissions to view email groups"
            }
        
        # Get all email groups
        email_groups = frappe.get_all("Email Group",
            fields=["name", "title", "description", "creation", "modified"],
            order_by="creation desc"
        )
        
        # Get subscriber count for each group
        for group in email_groups:
            subscriber_count = frappe.db.count("Email Group Member", {
                "email_group": group.name,
                "unsubscribed": 0
            })
            group["subscriber_count"] = subscriber_count
        
        return {
            "success": True,
            "email_groups": email_groups,
            "total_groups": len(email_groups)
        }
        
    except Exception as e:
        frappe.log_error(f"Get email groups error: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to get email groups: {str(e)}"
        }

@frappe.whitelist()
def create_email_group(title, description=None):
    """
    Create a new email group (Admin only)
    Requires authentication
    """
    try:
        # Check if user has permission to create email groups
        if not frappe.has_permission("Email Group", "create"):
            return {
                "success": False,
                "message": "Insufficient permissions to create email groups"
            }
        
        if not title:
            return {
                "success": False,
                "message": "Email group title is required"
            }
        
        # Check if email group with same title already exists
        if frappe.db.exists("Email Group", title):
            return {
                "success": False,
                "message": f"Email group '{title}' already exists"
            }
        
        # Create the email group
        email_group = frappe.get_doc({
            "doctype": "Email Group",
            "title": title,
            "description": description or f"Email group for {title}"
        })
        email_group.insert()
        frappe.db.commit()
        
        return {
            "success": True,
            "message": f"Email group '{title}' created successfully",
            "email_group": {
                "name": email_group.name,
                "title": email_group.title,
                "description": email_group.description
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Create email group error: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to create email group: {str(e)}"
        }

def send_welcome_email(email, full_name=None, support_email="info@rockettradeline.com", dashboard_link="www.rockettradeline.com"):
    """
    Send welcome email to user using the Welcome Email template
    
    Args:
        email (str): Recipient's email address
        full_name (str): Recipient's full name (optional)
        support_email (str): Support email address (default: info@rockettradeline.com)
        dashboard_link (str): Dashboard link (default: www.rockettradeline.com)
    
    Returns:
        dict: Success/failure status with message
    """
    try:
        # Validate email format
        if not email or not validate_email_address(email):
            return {
                "success": False,
                "message": "Please provide a valid email address"
            }
        
        # Prepare greeting name
        if not full_name:
            full_name = email.split('@')[0].title()
        
        # Prepare context for the email template
        context = {
            'full_name': full_name,
            'support_email': support_email,
            'dashboard_link': dashboard_link
        }
        
        # Send the email using the Welcome Email template
        result = send_email_from_template(
            template_name='Welcome Email',
            recipients=[email],
            context=context
        )
        
        if result.get('success'):
            frappe.logger().info(f"Welcome email sent successfully to {email}")
            return {
                "success": True,
                "message": f"Welcome email sent successfully to {email}",
                "email": email,
                "full_name": full_name
            }
        else:
            frappe.log_error(
                f"Failed to send welcome email to {email}: {result.get('error')}", 
                "Welcome Email Error"
            )
            return {
                "success": False,
                "message": f"Failed to send welcome email: {result.get('error', 'Unknown error')}"
            }
            
    except Exception as e:
        frappe.log_error(f"Welcome email error for {email}: {str(e)}", "Welcome Email Error")
        return {
            "success": False,
            "message": f"Welcome email failed: {str(e)}"
        }

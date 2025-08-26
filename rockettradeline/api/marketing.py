import frappe
from frappe import _
from frappe.utils import validate_email_address, now_datetime

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

@frappe.whitelist()
def get_newsletter_subscribers(limit=50, start=0):
    """
    Get list of newsletter subscribers (Admin only)
    Requires authentication
    """
    try:
        # Check if user has permission to view email groups
        if not frappe.has_permission("Email Group Member", "read"):
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

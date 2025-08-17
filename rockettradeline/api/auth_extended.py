from .auth import jwt_required, get_current_user
import frappe
from frappe import _
import json
import os

# Optional imports - handle gracefully if libraries are not installed
try:
    from google.oauth2 import id_token
    from google.auth.transport import requests
    GOOGLE_OAUTH_AVAILABLE = True
except ImportError:
    GOOGLE_OAUTH_AVAILABLE = False

try:
    import pyotp
    PYOTP_AVAILABLE = True
except ImportError:
    PYOTP_AVAILABLE = False

# Google OAuth Configuration
GOOGLE_CLIENT_ID = frappe.conf.get("google_client_id")

@frappe.whitelist(allow_guest=True)
def google_oauth_login(credential):
    """
    Handle Google OAuth login
    """
    try:
        if not GOOGLE_OAUTH_AVAILABLE:
            return {
                "success": False,
                "message": "Google OAuth libraries not installed"
            }
            
        if not GOOGLE_CLIENT_ID:
            return {
                "success": False,
                "message": "Google OAuth not configured"
            }
        
        # Verify the token
        idinfo = id_token.verify_oauth2_token(
            credential, requests.Request(), GOOGLE_CLIENT_ID
        )
        
        # Extract user information
        email = idinfo.get('email')
        name = idinfo.get('name')
        picture = idinfo.get('picture')
        
        if not email:
            return {
                "success": False,
                "message": "Email not provided by Google"
            }
        
        # Check if user exists
        user = None
        if frappe.db.exists("User", email):
            user = frappe.get_doc("User", email)
        else:
            # Create new user
            user = frappe.get_doc({
                "doctype": "User",
                "email": email,
                "full_name": name or email,
                "first_name": name.split()[0] if name else email.split('@')[0],
                "enabled": 1,
                "user_type": "Website User",
                "user_image": picture,
                "roles": [{"role": "Customer"}]
            })
            user.insert(ignore_permissions=True)
        
        # Login the user
        frappe.local.login_manager.login_as(user.name)
        
        return {
            "success": True,
            "message": "Login successful",
            "user": {
                "name": user.name,
                "email": user.email,
                "full_name": user.full_name,
                "user_image": user.user_image,
                "roles": [role.role for role in user.roles]
            }
        }
        
    except ValueError as e:
        return {
            "success": False,
            "message": "Invalid token"
        }
    except Exception as e:
        frappe.logger().error(f"Google OAuth error: {str(e)}")
        return {
            "success": False,
            "message": "Authentication failed"
        }

@frappe.whitelist(allow_guest=True)
def forgot_password(email):
    """
    Send password reset email
    """
    try:
        if not frappe.db.exists("User", email):
            return {
                "success": False,
                "message": "User not found"
            }
        
        user = frappe.get_doc("User", email)
        
        if not user.enabled:
            return {
                "success": False,
                "message": "Account is disabled"
            }
        
        # Generate password reset token
        from frappe.utils import random_string
        reset_token = random_string(32)
        
        # Save reset token (you'd need to add this field to User doctype)
        user.reset_password_token = reset_token
        user.reset_password_expires = frappe.utils.add_to_date(frappe.utils.now(), hours=24)
        user.save(ignore_permissions=True)
        
        # Send reset email
        reset_link = f"{frappe.utils.get_url()}/reset-password?token={reset_token}"
        
        frappe.sendmail(
            recipients=[email],
            subject="Password Reset Request",
            template="password_reset",
            args={
                "user": user.full_name or user.email,
                "reset_link": reset_link
            }
        )
        
        return {
            "success": True,
            "message": "Password reset email sent"
        }
        
    except Exception as e:
        frappe.logger().error(f"Password reset error: {str(e)}")
        return {
            "success": False,
            "message": "Failed to send reset email"
        }

@frappe.whitelist(allow_guest=True)
def reset_password(token, new_password):
    """
    Reset password using token
    """
    try:
        user = frappe.get_all("User", 
            filters={
                "reset_password_token": token,
                "reset_password_expires": [">", frappe.utils.now()],
                "enabled": 1
            },
            limit=1
        )
        
        if not user:
            return {
                "success": False,
                "message": "Invalid or expired token"
            }
        
        user_doc = frappe.get_doc("User", user[0].name)
        user_doc.new_password = new_password
        user_doc.reset_password_token = ""
        user_doc.reset_password_expires = ""
        user_doc.save(ignore_permissions=True)
        
        return {
            "success": True,
            "message": "Password reset successful"
        }
        
    except Exception as e:
        frappe.logger().error(f"Password reset error: {str(e)}")
        return {
            "success": False,
            "message": "Failed to reset password"
        }

@frappe.whitelist()
def change_password(old_password, new_password):
    """
    Change user password
    """
    try:
        user_name = get_current_user()
        if not user_name:
            return {"success": False, "message": "Authentication required"}
        user = frappe.get_doc("User", user_name)
        
        # Verify old password
        from frappe.auth import check_password
        if not check_password(user.name, old_password):
            return {
                "success": False,
                "message": "Invalid current password"
            }
        
        # Update password
        user.new_password = new_password
        user.save(ignore_permissions=True)
        
        return {
            "success": True,
            "message": "Password changed successfully"
        }
    except Exception as e:
        frappe.logger().error(f"Password change error: {str(e)}")
        return {
            "success": False,
            "message": "Failed to change password"
        }

@frappe.whitelist()
def enable_two_factor():
    """
    Enable two-factor authentication
    """
    try:
        if not PYOTP_AVAILABLE:
            return {
                "success": False,
                "message": "Two-factor authentication libraries not installed"
            }
        
        user_name = get_current_user()
        if not user_name:
            return {"success": False, "message": "Authentication required"}
        user = frappe.get_doc("User", user_name)
        
        # Generate secret key for 2FA
        secret = pyotp.random_base32()
        
        # Save secret (you'd need to add this field to User doctype)
        user.two_factor_secret = secret
        user.two_factor_enabled = 1
        user.save(ignore_permissions=True)
        
        # Generate QR code URL
        totp = pyotp.TOTP(secret)
        qr_url = totp.provisioning_uri(
            name=user.email,
            issuer_name="Rocket Tradeline"
        )
        
        return {
            "success": True,
            "message": "Two-factor authentication enabled",
            "secret": secret,
            "qr_url": qr_url
        }
    except Exception as e:
        frappe.logger().error(f"2FA enable error: {str(e)}")
        return {
            "success": False,
            "message": "Failed to enable 2FA"
        }

@frappe.whitelist()
def disable_two_factor():
    """
    Disable two-factor authentication
    """
    try:
        user_name = get_current_user()
        if not user_name:
            return {"success": False, "message": "Authentication required"}
        user = frappe.get_doc("User", user_name)
        
        user.two_factor_enabled = 0
        user.two_factor_secret = ""
        user.save(ignore_permissions=True)
        
        return {
            "success": True,
            "message": "Two-factor authentication disabled"
        }
    except Exception as e:
        frappe.logger().error(f"2FA disable error: {str(e)}")
        return {
            "success": False,
            "message": "Failed to disable 2FA"
        }

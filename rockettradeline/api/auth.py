
import frappe
from frappe import _
from frappe.auth import LoginManager
from frappe.utils import validate_email_address, random_string, cstr, encode, now_datetime, add_days, now
from frappe.core.doctype.user.user import sign_up as frappe_sign_up
from frappe.integrations.utils import make_post_request
import json
import hashlib
import secrets
import base64
from datetime import datetime, timedelta
import jwt
import os
from functools import wraps
from .utils import is_administrator
from frappe.utils.file_manager import save_file
from werkzeug.utils import secure_filename


def get_authenticated_user():
    """
    Returns the authenticated user set by jwt_required, or None if not authenticated.
    """
    user = frappe.session.user if hasattr(frappe.session, 'user') and frappe.session.user != "Guest" else None
    return user
# Route Protection Decorators

def jwt_required(allow_guest=False):
    """
    Decorator to protect routes with JWT authentication
    Automatically sets frappe.session.user after validating JWT token
    
    Args:
        allow_guest (bool): If True, allows guest access when no valid token is provided
    
    Usage:
        @frappe.whitelist(allow_guest=True)
        @jwt_required()
        def protected_endpoint():
            # frappe.session.user will be set to the authenticated user
            return {"user": frappe.session.user}
        
        @frappe.whitelist(allow_guest=True)
        @jwt_required(allow_guest=True)
        def optional_auth_endpoint():
            # Works with or without authentication
            if frappe.session.user != "Guest":
                return {"message": f"Hello {frappe.session.user}"}
            else:
                return {"message": "Hello Guest"}
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Get Authorization header - use custom header to avoid Frappe interference
                auth_header = frappe.get_request_header("X-Authorization") or frappe.get_request_header("Authorization")
                user_name = None
                
                if auth_header:
                    # Handle both "Bearer token" and just "token" formats
                    if auth_header.startswith("Bearer "):
                        # JWT Token authentication
                        jwt_token = auth_header.replace("Bearer ", "")
                        payload = validate_jwt_token(jwt_token)
                        if payload:
                            user_name = payload.get('user_id')
                    elif auth_header.startswith("token "):
                        # Legacy API token authentication
                        user_name = validate_token_auth(auth_header)
                
                # Set session user
                if user_name:
                    # Validate user exists and is enabled
                    if frappe.db.exists("User", user_name):
                        user_doc = frappe.get_doc("User", user_name)
                        if user_doc.enabled:
                            # Set the session user directly without using frappe.set_user
                            frappe.session.user = user_name
                            frappe.local.session_user = user_name
                        else:
                            user_name = None
                    else:
                        user_name = None
                
                # Handle authentication requirement
                if not user_name and not allow_guest:
                    frappe.local.response.http_status_code = 401
                    return {
                        "success": False,
                        "message": "Authentication required"
                    }
                
                # If no valid authentication and guest is allowed, ensure Guest user
                if not user_name and allow_guest:
                    frappe.set_user("Guest")
                
                # Call the original function
                return func(*args, **kwargs)
                
            except Exception as e:
                frappe.log_error(f"JWT decorator error: {str(e)}")
                if not allow_guest:
                    frappe.local.response.http_status_code = 401
                    return {
                        "success": False,
                        "message": "Authentication failed",
                        "error": str(e)
                    }
                else:
                    # Set guest user and continue
                    frappe.set_user("Guest")
                    return func(*args, **kwargs)
        
        return wrapper
    return decorator

def require_roles(*required_roles):
    """
    Decorator to require specific roles for accessing endpoints
    Must be used with @jwt_required()
    
    Usage:
        @frappe.whitelist(allow_guest=True)
        @jwt_required()
        @require_roles("System Manager", "Customer")
        def admin_endpoint():
            return {"message": "Admin access granted"}
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                if frappe.session.user == "Guest":
                    frappe.local.response.http_status_code = 401
                    return {
                        "success": False,
                        "message": "Authentication required"
                    }
                
                # Check user roles
                user_roles = frappe.get_roles(frappe.session.user)
                
                # Check if user has any of the required roles
                has_required_role = any(role in user_roles for role in required_roles)
                
                if not has_required_role:
                    frappe.local.response.http_status_code = 403
                    return {
                        "success": False,
                        "message": f"Requires one of these roles: {', '.join(required_roles)}"
                    }
                
                return func(*args, **kwargs)
                
            except Exception as e:
                frappe.log_error(f"Role check error: {str(e)}")
                frappe.local.response.http_status_code = 500
                return {
                    "success": False,
                    "message": "Permission check failed"
                }
        
        return wrapper
    return decorator

# Token Management Helper Functions

def get_or_create_jwt_secret():
    """Get or create a secure JWT secret for the site"""
    try:
        # Try to get existing secret from site config
        secret = frappe.conf.get('jwt_secret')
        if not secret:
            # Generate a deterministic secret based on site and system info
            site_name = getattr(frappe.local, 'site', 'default_site')
            
            # Create a secure secret using site name and a fixed salt
            secret_base = f"{site_name}_jwt_secret_2024"
            secret = hashlib.sha256(secret_base.encode()).hexdigest()
            
            # Add some entropy from the site
            secret = hashlib.sha256(f"{secret}{site_name}".encode()).hexdigest()
            
        return secret
    except Exception as e:
        # Fallback secret - use a deterministic approach
        try:
            site_name = getattr(frappe.local, 'site', 'default_site')
            fallback_secret = hashlib.sha256(f"{site_name}_fallback_jwt_2024".encode()).hexdigest()
            return fallback_secret
        except:
            # Ultimate fallback
            return hashlib.sha256("default_jwt_secret_2024".encode()).hexdigest()

def generate_jwt_token(user_name, expires_in_hours=24):
    """Generate a secure JWT token with user information"""
    try:
        # Get user details
        user_doc = frappe.get_doc("User", user_name)
        
        # Calculate timestamps (JWT requires Unix timestamps)
        now_timestamp = datetime.utcnow().timestamp()
        exp_timestamp = (datetime.utcnow() + timedelta(hours=expires_in_hours)).timestamp()
        
        # Create payload with user information
        payload = {
            'user_id': user_name,
            'email': user_doc.email,
            'full_name': user_doc.full_name,
            'user_type': user_doc.user_type,
            'iat': int(now_timestamp),
            'exp': int(exp_timestamp),
            'iss': frappe.local.site,  # Issuer
            'sub': user_name,  # Subject
        }
        
        # Get JWT secret
        secret = get_or_create_jwt_secret()
        
        # Generate JWT token
        token = jwt.encode(payload, secret, algorithm='HS256')
        
        # Handle PyJWT version compatibility (some return bytes, some return string)
        if isinstance(token, bytes):
            token = token.decode('utf-8')
        
        return token
        
    except Exception as e:
        frappe.log_error(f"JWT token generation failed for user: {user_name}: {str(e)}")
        raise e

def validate_jwt_token(token):
    """Validate and decode JWT token"""
    try:
        if not token:
            frappe.log_error("JWT token is empty", "JWT Validation")
            return None
            
        # Get JWT secret
        secret = get_or_create_jwt_secret()
        
        # Decode and validate token
        payload = jwt.decode(token, secret, algorithms=['HS256'])
        
        # Check if user still exists and is active
        user_id = payload.get('user_id')
        if not user_id:
            frappe.log_error(f"No user_id in JWT payload: {payload}", "JWT Validation")
            return None
            
        if frappe.db.exists("User", user_id):
            user_doc = frappe.get_doc("User", user_id)
            if user_doc.enabled:
                return payload
            else:
                frappe.log_error(f"User {user_id} is disabled", "JWT Validation")
        else:
            frappe.log_error(f"User {user_id} does not exist", "JWT Validation")
        
        return None
        
    except jwt.ExpiredSignatureError as e:
        frappe.log_error(f"JWT token expired: {str(e)}", "JWT Validation")
        return None
    except jwt.InvalidTokenError as e:
        frappe.log_error(f"Invalid JWT token: {str(e)}", "JWT Validation")
        return None
    except Exception as e:
        frappe.log_error(f"JWT validation error: {str(e)}", "JWT Validation")
        return None

def validate_authorization_header():
    """Validate the Authorization header and return user info"""
    try:
        auth_header = frappe.get_request_header("Authorization")
        if not auth_header:
            return None
            
        # Check if it's a Bearer token
        if auth_header.startswith("Bearer "):
            jwt_token = auth_header.replace("Bearer ", "")
            payload = validate_jwt_token(jwt_token)
            if payload:
                return payload.get('user_id')
        
        return None
        
    except Exception:
        return None

def generate_authorization_token(user_name):
    """Generate a secure JWT authorization token for the user"""
    try:
        # Generate JWT token
        jwt_token = generate_jwt_token(user_name)
        
        return f"Bearer {jwt_token}", jwt_token
        
    except Exception:
        frappe.log_error(f"Failed to generate auth token for user: {user_name}")
        raise

def validate_authorization_token(auth_header):
    """Validate authorization token from header"""
    try:
        if not auth_header:
            return None, "Authorization header missing"
            
        # Handle both "Bearer token" and "token api_key:api_secret" formats
        if auth_header.startswith("Bearer "):
            # Decode the base64 token
            token = auth_header.replace("Bearer ", "")
            try:
                decoded = base64.b64decode(token).decode()
                if ":" in decoded:
                    api_key, api_secret = decoded.split(":", 1)
                    auth_string = f"token {api_key}:{api_secret}"
                else:
                    return None, "Invalid token format"
            except Exception:
                return None, "Invalid token encoding"
        elif auth_header.startswith("token "):
            auth_string = auth_header
        else:
            return None, "Invalid authorization format"
            
        # Validate using existing token validation
        return validate_token_auth(auth_string)
        
    except Exception:
        return None, "Token validation failed"

def generate_api_key_secret():
    """Generate API key and secret for user"""
    api_key = frappe.generate_hash(length=15)
    api_secret = frappe.generate_hash(length=40)
    return api_key, api_secret

def create_user_tokens(user_name):
    """Create API tokens for user"""
    try:
        # Generate API key and secret
        api_key, api_secret = generate_api_key_secret()
        
        # Update user with API credentials
        user = frappe.get_doc("User", user_name)
        user.api_key = api_key
        user.api_secret = api_secret
        user.save(ignore_permissions=True)
        
        return api_key, api_secret
    except Exception:
        frappe.log_error(f"Failed to create tokens for user: {user_name}")
        raise

def get_user_tokens(user_name):
    """Get existing API tokens for user or create new ones"""
    try:
        user = frappe.get_doc("User", user_name)
        
        # If user doesn't have tokens, create them
        if not user.api_key or not user.api_secret:
            api_key, api_secret = create_user_tokens(user_name)
        else:
            api_key = user.api_key
            api_secret = user.api_secret
        
        return api_key, api_secret
    except Exception:
        frappe.log_error(f"Failed to get tokens for user: {user_name}")
        raise

def validate_token_auth(token):
    """Validate API token and return user"""
    try:
        # Token format: "token api_key:api_secret"
        if not token.startswith("token "):
            return None
        
        auth_string = token.replace("token ", "")
        if ":" not in auth_string:
            return None
        
        api_key, api_secret = auth_string.split(":", 1)
        
        # Find user with this API key
        user = frappe.get_all("User", 
            filters={"api_key": api_key},
            fields=["name", "api_secret", "enabled"],
            limit=1
        )
        
        if not user:
            return None
        
        user_doc = user[0]
        
        # Check if user is enabled
        if not user_doc.enabled:
            return None
        
        # Validate API secret
        if user_doc.api_secret != api_secret:
            return None
        
        return user_doc.name
    except Exception:
        return None

# Email Verification Functions

# Email Template Functions

def get_email_header(logo_height="60px", logo_width="200px"):
    """Generate consistent email header with Rocket Tradeline branding"""
    site_url = "https://api.rockettradeline.com"
    site_logo = f"{site_url}/assets/rockettradeline/logo.png"
    
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f5f5f5;">
        <div style="background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            <!-- Header with Logo -->
            <div style="padding: 30px 30px 20px 30px; text-align: center;">
                <div style="margin-bottom: 20px;">
                    <a href="https://www.rockettradeline.com" target="_blank" style="text-decoration: none;">
                        <img src="{site_logo}" alt="Rocket Tradeline" style="max-height: {logo_height}; max-width: {logo_width};" />
                    </a>
                </div>
            </div>
            
            <!-- Main Content -->
            <div style="padding: 0 30px 30px 30px;">"""

def get_email_footer(recipient_email):
    """Generate consistent email footer with Rocket Tradeline branding"""
    site_url = "https://api.rockettradeline.com"
    site_logo = f"{site_url}/assets/rockettradeline/logo.png"
    
    # Get social media links from Site Content doctype
    social_media_links = {}
    try:
        # Fetch social media links from Site Content where section=social
        social_records = frappe.get_all(
            "Site Content",
            filters={"section": "social"},
            fields=["name", "value"]
        )
        
        # Convert to dictionary for easy access
        for record in social_records:
            social_media_links[record.name] = record.value
    except Exception as e:
        frappe.log_error(f"Error fetching social media links: {str(e)}")
        # Default to empty links if there's an error
        social_media_links = {}
    
    # Helper function to get social media icon
    def get_social_icon(platform, url):
        if not url or url.strip() == "":
            return ""
        
        # Icon URLs and colors for different platforms
        platform_config = {
            "facebook": {
                "icon_url": "https://cdn-icons-png.flaticon.com/512/124/124010.png",
                "alt": "Facebook"
            },
            "twitter": {
                "icon_url": "https://cdn-icons-png.flaticon.com/512/124/124021.png", 
                "alt": "Twitter"
            },
            "instagram": {
                "icon_url": "https://cdn-icons-png.flaticon.com/512/2111/2111463.png",
                "alt": "Instagram"
            },
            "pinterest": {
                "icon_url": "https://cdn-icons-png.flaticon.com/512/145/145808.png",
                "alt": "Pinterest"
            },
            "tiktok": {
                "icon_url": "https://cdn-icons-png.flaticon.com/512/3046/3046120.png",
                "alt": "TikTok"
            }
        }
        
        platform_lower = platform.lower().replace("social_", "")
        config = platform_config.get(platform_lower, {
            "icon_url": "https://cdn-icons-png.flaticon.com/512/733/733579.png",
            "alt": "Social Media"
        })
        
        return f'''
        <a href="{url}" style="display: inline-block; margin: 0 8px; text-decoration: none;" target="_blank">
            <img src="{config["icon_url"]}" alt="{config["alt"]}" style="width: 32px; height: 32px; border-radius: 6px; transition: opacity 0.3s; opacity: 0.8;" onmouseover="this.style.opacity='1'" onmouseout="this.style.opacity='0.8'" />
        </a>'''
    
    # Build social media icons HTML
    social_icons_html = ""
    social_platforms = ["social_facebook", "social_twitter", "social_instagram", "social_pinterest", "social_tiktok"]
    
    for platform in social_platforms:
        if platform in social_media_links:
            social_icons_html += get_social_icon(platform, social_media_links[platform])
    
    # If no social media links found, show placeholder
    if not social_icons_html.strip():
        social_icons_html = '''
        <a href="#" style="display: inline-block; margin: 0 8px; text-decoration: none;">
            <img src="https://cdn-icons-png.flaticon.com/512/124/124010.png" alt="Facebook" style="width: 32px; height: 32px; border-radius: 6px; opacity: 0.3;" />
        </a>
        <a href="#" style="display: inline-block; margin: 0 8px; text-decoration: none;">
            <img src="https://cdn-icons-png.flaticon.com/512/124/124021.png" alt="Twitter" style="width: 32px; height: 32px; border-radius: 6px; opacity: 0.3;" />
        </a>
        <a href="#" style="display: inline-block; margin: 0 8px; text-decoration: none;">
            <img src="https://cdn-icons-png.flaticon.com/512/124/124024.png" alt="Instagram" style="width: 32px; height: 32px; border-radius: 6px; opacity: 0.3;" />
        </a>'''
    
    return f"""
            </div>
            
            <!-- Footer with Logo and Social Links -->
            <div style="background-color: #f9fafb; padding: 30px; text-align: center; border-top: 1px solid #e5e7eb;">
                <!-- Bottom Logo -->
                <div style="margin-bottom: 20px;">
                    <img src="{site_logo}" alt="Rocket Tradeline" style="max-height: 40px; max-width: 150px;" />
                </div>
                
                <!-- Social Media Icons -->
                <div style="margin-bottom: 20px;">
                    {social_icons_html}
                </div>
                
                <!-- Footer Text -->
                <div style="font-size: 12px; color: #9ca3af;">
                    <p style="margin: 0 0 10px 0;">
                        This email was sent to {recipient_email}. If you'd rather not receive this kind of email, you can 
                        <a href="#" style="color: #17B26A; text-decoration: none;">unsubscribe</a> or 
                        <a href="#" style="color: #17B26A; text-decoration: none;">manage your email preferences</a>.
                    </p>
                    
                    <!-- Contact Information -->
                    <div style="background-color: #f3f4f6; padding: 15px; border-radius: 6px; margin: 15px 0; text-align: center;">
                        <p style="margin: 0 0 10px 0; color: #374151; font-weight: 600; font-size: 14px;">📞 Need Help? Contact Us:</p>
                        <p style="margin: 5px 0; color: #6b7280; font-size: 13px;">
                            <strong>Phone:</strong> <a href="tel:+14696777948" style="color: #17B26A; text-decoration: none;">(469) 677-7948</a>
                        </p>
                        <p style="margin: 5px 0; color: #6b7280; font-size: 13px;">
                            <strong>Email:</strong> <a href="mailto:info@rockettradeline.com" style="color: #17B26A; text-decoration: none;">info@rockettradeline.com</a>
                        </p>
                        <p style="margin: 5px 0; color: #6b7280; font-size: 13px;">
                            <a href="https://calendar.app.google/WJmAbuqdfrFUJ6Z4A" style="color: #17B26A; text-decoration: none; font-weight: 600;">📅 Schedule a Call</a>
                        </p>
                    </div>
                    
                    <p style="margin: 0 0 15px 0;">© 2025 Rocket Tradelines. All rights reserved</p>
                    
                    <!-- Confidentiality Disclaimer -->
                    <div style="background-color: #fef3c7; border: 1px solid #f59e0b; padding: 12px; border-radius: 6px; margin: 15px 0;">
                        <p style="margin: 0; color: #92400e; font-size: 11px; line-height: 1.4; text-align: left;">
                            <strong>Confidentiality Disclaimer:</strong> The information contained in this e-mail may be privileged and/or confidential, and protected from disclosure, and no waiver of any attorney-client, work product, or other privilege is intended. If you are the intended recipient, further disclosures are prohibited without proper authorization. If you are not the intended recipient (or have received this e-mail in error) please notify the sender immediately and destroy this e-mail. Any unauthorized copying, disclosure or distribution of the material in this e-mail is strictly forbidden and possibly a violation of federal or state law and regulations. The sender and Rocket Tradeline, and its affiliated entities, hereby expressly reserve all privileges and confidentiality that might otherwise be waived as a result of an erroneous or misdirected e-mail transmission. No employee or agent is authorized to conclude any binding agreement on behalf of Rocket Tradeline, or any affiliated entity, by e-mail without express written confirmation by the Owner or other duly authorized representative of Rocket Tradeline.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    </div>"""

def generate_verification_token(email):
    """Generate email verification token"""
    try:
        # Check if user exists first
        if not frappe.db.exists("User", email):
            frappe.log_error(f"User {email} does not exist when generating verification token")
            return None
            
        # Create a unique verification token
        token_data = f"{email}:{now()}:{random_string(32)}"
        verification_token = base64.b64encode(token_data.encode()).decode()
        
        # Store verification token in User doc using correct field names
        frappe.db.set_value("User", email, "email_verification_token", verification_token)
        frappe.db.set_value("User", email, "email_verification_sent_at", now_datetime())
        frappe.db.commit()
        
        frappe.logger().info(f"Successfully generated verification token for {email}")
        return verification_token
        
    except Exception as e:
        frappe.log_error(f"Error generating verification token: {str(e)}", "Verification Token Error")
        return None

def send_verification_email(user_email, full_name, verification_token):
    """Send email verification email using Email Template Custom system"""
    try:
        # Create verification link
        site_url = frappe.utils.get_url()
        verification_link = f"{site_url}/api/method/rockettradeline.api.auth.verify_email?token={verification_token}"
        
        # Check if there's a default outgoing email account
        email_accounts = frappe.get_all('Email Account', 
            filters={'enable_outgoing': 1, 'default_outgoing': 1},
            fields=['name', 'email_id', 'password']
        )
        
        if not email_accounts:
            frappe.log_error("No default outgoing email account configured", "Email Configuration Error")
            return False
            
        email_account = email_accounts[0]
        
        # Check if email account has password configured
        account_doc = frappe.get_doc('Email Account', email_account.name)
        if not account_doc.password:
            # Log the configuration issue but still queue the email
            frappe.log_error(f"Email account '{email_account.name}' has no password. Email will be queued but may fail to send to {user_email}", "Email Config Warning")
        
        # Try to use Email Template Custom first
        try:
            # Check if Email Template Custom exists and template is available
            if frappe.db.exists('DocType', 'Email Template Custom') and frappe.db.exists('Email Template Custom', 'Email Verification'):
                # Use the Email Template Custom system
                from rockettradeline.utils.email_templates import send_email_from_template
                
                # Prepare context for template
                context = {
                    'full_name': full_name,
                    'site_name': 'Rocket Tradeline',
                    'verification_link': verification_link,
                    'recipient_email': user_email
                }
                
                # Send email using template
                result = send_email_from_template('Email Verification', user_email, context)
                
                if result.get('success'):
                    frappe.logger().info(f"Verification email sent using template to {user_email}")
                    return True
                else:
                    frappe.log_error(f"Template email failed for {user_email}: {result.get('error')}", "Template Email Error")
                    # Fall back to hardcoded email below
            else:
                frappe.logger().info("Email Template Custom not available, using fallback method")
        
        except Exception as template_error:
            frappe.log_error(f"Template email system failed for {user_email}: {str(template_error)}", "Template Email System Error")
            # Fall back to hardcoded email below
        
        # Fallback: Send email using Email Template Custom system
        try:
            from rockettradeline.rockettradeline.doctype.email_template_custom.email_template_custom import send_email_template
            
            # Prepare template parameters
            template_params = {
                "full_name": full_name,
                "site_name": frappe.local.site,
                "verification_link": verification_link
            }
            
            # Send email using template
            send_email_template(
                template_name="Email Verification",
                recipients=[user_email],
                parameters=template_params
            )
            
            frappe.logger().info(f"Verification email sent using Email Template Custom to {user_email}")
            return True
            
        except Exception as e:
            frappe.log_error(f"Email Template Custom failed for {user_email}: {str(e)}", "Email Template Custom Error") 
            return False
        
    except Exception as e:
        frappe.log_error(f"Email send failed for {user_email}: {str(e)}", "Email Sending Error")
        return False

def is_email_verified(email):
    """Check if user email is verified"""
    try:
        user = frappe.get_doc("User", email)
        return getattr(user, 'email_verified', False)
    except:
        return False


def get_roles_from_role_profile(role_profile_name, fallback_roles=None):
    """Return list of role dicts for a given Role Profile name.

    Returns a list suitable for assigning to User.roles, e.g.
    [{"role": "Customer"}, {"role": "Sales User"}].

    If the role profile is missing or an error occurs, returns fallback_roles
    (defaults to [{"role": "Customer"}]).
    """
    if fallback_roles is None:
        fallback_roles = [{"role": "Customer"}]

    try:
        if not role_profile_name:
            return fallback_roles

        # Ensure Role Profile exists
        if not frappe.db.exists("Role Profile", role_profile_name):
            return fallback_roles

        rp = frappe.get_doc("Role Profile", role_profile_name)

        roles = []
        # Role Profile usually has a child table named 'roles' with field 'role'
        for r in getattr(rp, 'roles', []) or []:
            # support dict-like or object rows
            if isinstance(r, dict):
                role_name = r.get('role')
            else:
                role_name = getattr(r, 'role', None)

            if role_name:
                roles.append({"role": role_name})

        if roles:
            return roles

        return fallback_roles
    except Exception:
        return fallback_roles

# Authentication APIs

@frappe.whitelist(allow_guest=True)
def login(usr, pwd):
    """
    Login with username/email and password and return API tokens
    """
    try:
        # Clear any existing session first
        frappe.local.session_obj = None
        frappe.session.user = "Guest"
        
        # Validate input parameters
        if not usr or not pwd:
            frappe.local.response.http_status_code = 400
            return {
                "success": False,
                "message": "Username and password are required"
            }
        
        # Check if user exists and is enabled
        user_doc = None
        try:
            # Try to find user by email or username
            if validate_email_address(usr):
                user_doc = frappe.get_doc("User", usr)
            else:
                # Check if username exists
                users = frappe.get_all("User", filters={"username": usr}, fields=["name"])
                if users:
                    user_doc = frappe.get_doc("User", users[0].name)
                else:
                    # Try email field
                    users = frappe.get_all("User", filters={"email": usr}, fields=["name"])
                    if users:
                        user_doc = frappe.get_doc("User", users[0].name)
        except frappe.DoesNotExistError:
            pass
        
        if not user_doc:
            frappe.local.response.http_status_code = 401
            return {
                "success": False,
                "message": "Invalid credentials"
            }
        
        # Check if user is enabled
        if not user_doc.enabled:
            frappe.local.response.http_status_code = 401
            return {
                "success": False,
                "message": "User account is disabled. Please contact your System Administrator."
            }
        
        # Verify password
        from frappe.utils.password import check_password
        if not check_password(user_doc.name, pwd):
            frappe.local.response.http_status_code = 401
            return {
                "success": False,
                "message": "Invalid credentials"
            }
        
        # Check if email is verified
        if not is_email_verified(user_doc.email):
            # Generate and send verification email
            try:
                verification_token = generate_verification_token(user_doc.email)
                if verification_token:
                    email_sent = send_verification_email(user_doc.email, user_doc.full_name, verification_token)
                    
                    message = "Please verify your email address before logging in."
                    if email_sent:
                        message += " A new verification email has been sent to your inbox."
                    else:
                        message += " Please contact support for assistance with email verification."
                        
                else:
                    message = "Please verify your email address before logging in. Please contact support for assistance."
                    
            except Exception as e:
                frappe.log_error(f"Failed to send verification email during login: {str(e)}")
                message = "Please verify your email address before logging in. Please contact support for assistance."
            
            frappe.local.response.http_status_code = 403
            return {
                "success": False,
                "message": message,
                "error_code": "EMAIL_NOT_VERIFIED",
                "email_sent": email_sent if 'email_sent' in locals() else False
            }
        
        # Set session for the authenticated user
        frappe.set_user(user_doc.name)
        
        # Generate JWT authorization token
        jwt_token = generate_jwt_token(user_doc.name)
        
        # Get customer information if exists
        customer = None
        customer_data = frappe.get_all("Customer", 
            filters={"user": user_doc.name},
            fields=["name", "customer_name", "customer_type", "email_id", "mobile_no", "territory"],
            limit=1
        )
        
        if customer_data:
            customer = customer_data[0]
        
        response_data = {
            "success": True,
            "message": "Login successful",
            "authorization_token": f"Bearer {jwt_token}",
            "token_type": "Bearer",
            "expires_in": 86400,  # 24 hours in seconds
            "user": {
                "name": user_doc.name,
                "email": user_doc.email,
                "full_name": user_doc.full_name,
                "user_image": user_doc.user_image,
                "phone": user_doc.phone,
                "role_profile_name": user_doc.role_profile_name,
                "roles": [role.role for role in user_doc.roles]
            }
        }
        
        if customer:
            response_data["customer"] = customer
        
        return response_data
        
    except frappe.AuthenticationError:
        frappe.local.response.http_status_code = 401
        return {
            "success": False,
            "message": "Invalid credentials"
        }
    except Exception as e:
        frappe.log_error(f"Login error: {str(e)}")
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": "An error occurred during login. Please try again."
        }

@frappe.whitelist(allow_guest=True)
def google_login(id_token):
    """
    Login with Google OAuth
    """
    try:
        # This would require google-auth library
        # For now, placeholder implementation
        frappe.local.response.http_status_code = 501
        return {
            "success": False,
            "message": "Google login not implemented yet"
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist(allow_guest=True)
def sign_up(email, full_name, password=None, phone=None, is_seller=0, is_buyer=0, is_broker=0 ):
    """
    Sign up new user, send verification email, and create customer record
    """
    try:
        # Validate email
        if not validate_email_address(email):
            frappe.local.response.http_status_code = 400
            return {
                "success": False,
                "message": "Invalid email address"
            }
        
        # Check if user already exists
        if frappe.db.exists("User", email):
            frappe.local.response.http_status_code = 409
            return {
                "success": False,
                "message": "User already exists"
            }
        
        # Validate password
        if password and len(password) < 6:
            frappe.local.response.http_status_code = 400
            return {
                "success": False,
                "message": "Password must be at least 6 characters long"
            }
            
            
        role_profile_name = "Tradeline Buyer"
        
        if int(is_seller) and not int(is_buyer) and not int(is_broker):
            role_profile_name = "Tradeline Seller"
        elif int(is_broker) and not int(is_buyer) and not int(is_seller):
            role_profile_name = "Tradeline Broker"
        
        # Determine roles from the selected role profile. Fall back to Customer role on errors.
        roles_list = get_roles_from_role_profile(role_profile_name)

        # Create user (initially unverified)
        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "full_name": full_name,
            "first_name": full_name.split()[0] if full_name else email,
            "last_name": full_name.split()[1] if full_name and len(full_name.split()) > 1 else None,
            "enabled": 1,
            "role_profile_name": role_profile_name,
            "user_type": "Website User",
            "roles": roles_list,
            "email_verified": 0,  # Initially unverified
            "send_welcome_email": 0  # Prevent default welcome email
        })
        
        if password:
            user.new_password = password
        
        if phone:
            user.phone = phone
        
        # Insert user and commit to ensure it exists before setting custom fields
        user.insert(ignore_permissions=True)
        frappe.db.commit()
        
        # Generate verification token
        verification_token = generate_verification_token(email)
        if not verification_token:
            # Rollback user creation
            frappe.delete_doc("User", email, ignore_permissions=True)
            frappe.local.response.http_status_code = 500
            return {
                "success": False,
                "message": "Failed to generate verification token"
            }
        
        # Send verification email
        email_sent = send_verification_email(email, full_name, verification_token)
        if not email_sent:
            # Log but don't fail the signup process
            print(f"Note: Email not sent to {email} due to configuration. User can still verify manually.")
        
        
        # Create customer record
        customer = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": full_name,
            "customer_type": "Individual",
            "customer_group": "Individual",
            "territory": "All Territories",
            "email_id": email,
            "mobile_no": phone,
            "user": user.name,
            # account_manager intentionally omitted for self sign-ups; only set when broker/admin creates client
            "is_primary_contact": 1,
            "is_seller": int(is_seller),
            "is_buyer": int(is_buyer),
            "is_broker": int(is_broker)
        })
        
        customer.insert(ignore_permissions=True)
        
        return {
            "success": True,
            "message": "Account created successfully! Please check your email to verify your account before logging in.",
            "email_sent": email_sent,
            "user": {
                "name": user.name,
                "email": user.email,
                "full_name": user.full_name,
                "phone": user.phone,
                "email_verified": False
            },
            "customer": {
                "name": customer.name,
                "customer_name": customer.customer_name,
                "customer_type": customer.customer_type,
                "email_id": customer.email_id,
                "mobile_no": customer.mobile_no
            }
        }
    except Exception as e:
        frappe.log_error(f"Sign up error: {str(e)}")
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": "An error occurred during registration. Please try again."
        }


@frappe.whitelist(allow_guest=True)
@jwt_required()
@require_roles("Tradeline Broker", "System Manager")
def broker_login_as_customer(email):
    """
    Allow a broker to obtain a JWT and login-as for a customer they manage.

    Verifies that the Customer with the provided email_id exists and that
    its `account_manager` equals the currently authenticated broker (via
    get_authenticated_user()). Returns the same response shape as `login()`
    including an authorization_token for the customer user.
    """
    try:
        broker_user = get_authenticated_user()
        if not broker_user:
            frappe.local.response.http_status_code = 401
            return {"success": False, "message": "Authentication required"}

        # Find customer by email_id
        customer_list = frappe.get_all("Customer",
            filters={"email_id": email},
            fields=["name", "account_manager", "customer_name", "customer_type", "email_id", "mobile_no", "territory"],
            limit=1
        )

        if not customer_list:
            frappe.local.response.http_status_code = 404
            return {"success": False, "message": "Customer not found"}

        customer_row = customer_list[0]

        # Ensure the broker manages this customer
        if not customer_row.get('account_manager') or customer_row.get('account_manager') != broker_user:
            frappe.local.response.http_status_code = 403
            return {"success": False, "message": "Not authorized to act as this customer"}

        # Resolve associated User for the customer
        user_name = email
        if not user_name:
            # Fallback: find User by email
            users = frappe.get_all("User", filters={"email": email}, fields=["name"], limit=1)
            if users:
                user_name = users[0].name

        if not user_name or not frappe.db.exists("User", user_name):
            frappe.local.response.http_status_code = 404
            return {"success": False, "message": "User for this customer not found"}

        user_doc = frappe.get_doc("User", user_name)
        if not user_doc.enabled:
            frappe.local.response.http_status_code = 403
            return {"success": False, "message": "Customer account is disabled"}

        # Generate JWT token for the customer user
        jwt_token = generate_jwt_token(user_doc.name)

        # Prepare response mirroring login()
        response_data = {
            "success": True,
            "message": "Login successful",
            "authorization_token": f"Bearer {jwt_token}",
            "token_type": "Bearer",
            "expires_in": 86400,  # 24 hours
            "user": {
                "name": user_doc.name,
                "email": user_doc.email,
                "full_name": user_doc.full_name,
                "user_image": user_doc.user_image,
                "phone": user_doc.phone,
                "role_profile_name": user_doc.role_profile_name,
                "roles": [role.role for role in user_doc.roles]
            }
        }

        # Attach the customer info if available
        response_data["customer"] = {
            "name": customer_row.get('name'),
            "customer_name": customer_row.get('customer_name'),
            "customer_type": customer_row.get('customer_type'),
            "email_id": customer_row.get('email_id'),
            "mobile_no": customer_row.get('mobile_no'),
            "territory": customer_row.get('territory')
        }

        return response_data
    except Exception as e:
        frappe.log_error(f"Broker impersonation error: {str(e)}")
        frappe.local.response.http_status_code = 500
        return {"success": False, "message": "An error occurred while attempting to impersonate the customer.", "error": str(e)}

@frappe.whitelist()
def logout():
    """
    Logout current user
    """
    try:
        frappe.local.login_manager.logout()
        return {
            "success": True,
            "message": "Logged out successfully"
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def get_tokens():
    """
    Get API tokens for current user
    """
    try:
        if frappe.session.user == "Guest":
            frappe.local.response.http_status_code = 401
            return {
                "success": False,
                "message": "Not authenticated"
            }
        
        api_key, api_secret = get_user_tokens(frappe.session.user)
        
        return {
            "success": True,
            "token": f"token {api_key}:{api_secret}",
            "api_key": api_key,
            "api_secret": api_secret
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def regenerate_tokens():
    """
    Regenerate authorization token for current user
    """
    try:
        if frappe.session.user == "Guest":
            frappe.local.response.http_status_code = 401
            return {
                "success": False,
                "message": "Not authenticated"
            }
        
        # Generate new authorization token
        token_string, auth_token = generate_authorization_token(frappe.session.user)
        
        return {
            "success": True,
            "message": "New authorization token generated successfully",
            "authorization_token": auth_token
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def revoke_tokens():
    """
    Revoke API tokens for current user
    """
    try:
        if frappe.session.user == "Guest":
            frappe.local.response.http_status_code = 401
            return {
                "success": False,
                "message": "Not authenticated"
            }
        
        # Clear tokens
        user = frappe.get_doc("User", frappe.session.user)
        user.api_key = ""
        user.api_secret = ""
        user.save(ignore_permissions=True)
        
        return {
            "success": True,
            "message": "Tokens revoked successfully"
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist(allow_guest=True)
def validate_token():
    """
    Validate API token from Authorization header
    """
    try:
        # Get token from Authorization header
        auth_header = frappe.get_request_header("Authorization")
        
        if not auth_header:
            frappe.local.response.http_status_code = 401
            return {
                "success": False,
                "message": "Authorization header missing"
            }
        
        # Validate token
        user_name = validate_token_auth(auth_header)
        
        if not user_name:
            frappe.local.response.http_status_code = 401
            return {
                "success": False,
                "message": "Invalid token"
            }
        
        # Get user details
        user = frappe.get_doc("User", user_name)
        
        # Get customer information if exists
        customer = None
        customer_data = frappe.get_all("Customer", 
            filters={"user": user.name},
            fields=["name", "customer_name", "customer_type", "email_id", "mobile_no", "territory"],
            limit=1
        )
        
        if customer_data:
            customer = customer_data[0]
        
        response_data = {
            "success": True,
            "valid": True,
            "user": {
                "name": user.name,
                "email": user.email,
                "full_name": user.full_name,
                "user_image": user.user_image,
                "phone": user.phone,
                "roles": [role.role for role in user.roles]
            }
        }
        
        if customer:
            response_data["customer"] = customer
        
        return response_data
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_current_user():
    """
    Get current user details with full customer document including child tables
    Automatically authenticated via JWT decorator
    """
    try:
        user_name = get_authenticated_user()
        if not user_name:
            frappe.local.response.http_status_code = 401
            return {"success": False, "message": "Authentication required"}
        user = frappe.get_doc("User", user_name)
        
        # Get full customer document with child tables if exists
        customer = None
        customer_list = frappe.get_all("Customer", 
            filters={"email_id": user.name},
            fields=["name"],
            limit=1
        )
        
        if customer_list:
            # Get the complete customer document with all child tables
            customer_doc = frappe.get_doc("Customer", customer_list[0].name)
            
            # Convert to dict to include child tables
            customer = customer_doc.as_dict()
            
            # Ensure the new flags are included with proper defaults
            customer['is_seller'] = bool(getattr(customer_doc, 'is_seller', 0))
            customer['has_signed_agreement'] = bool(getattr(customer_doc, 'has_signed_agreement', 0))
            customer['is_questionnaire_filled'] = bool(getattr(customer_doc, 'is_questionnaire_filled', 0))
            customer['agreement_signed_date'] = getattr(customer_doc, 'agreement_signed_date', None)
            customer['questionnaire_filled_date'] = getattr(customer_doc, 'questionnaire_filled_date', None)
            customer['custom_preferred_mode_of_payment'] = getattr(customer_doc, 'custom_preferred_mode_of_payment', None)
            
            # Remove system fields that aren't needed in API response
            system_fields = ['docstatus', 'idx', 'owner', 'modified_by', 'creation', 'modified']
            for field in system_fields:
                customer.pop(field, None)
        
        # Get user files/attachments - only latest from each folder
        all_user_files = frappe.get_all("File",
            filters={
                # "owner": user.name,
                "attached_to_doctype": "Customer",
                "attached_to_name": customer_list[0].name if customer_list else "1234"
                
            },
            fields=[
                "name", "file_url", "folder", "creation"
            ],
            order_by="creation desc"
        )
        
        # Group files by folder and get only the latest from each folder
        user_files = []
        seen_folders = set()
        
        for file_doc in all_user_files:
            folder_name = file_doc.get('folder', 'Home')
            if folder_name not in seen_folders:
                seen_folders.add(folder_name)
                # Remove creation field from the final result
                user_files.append({
                    "name": file_doc.get("name"),
                    "file_url": file_doc.get("file_url"),
                    "folder": file_doc.get("folder")
                })
        
        # Get role profile information
        role_profile_name = getattr(user, 'role_profile_name', None)
        role_profile_data = None
        
        if False:
            try:
                role_profile_doc = frappe.get_doc("Role Profile", role_profile_name)
                role_profile_data = {
                    "name": role_profile_doc.name,
                    "role_profile": role_profile_doc.role_profile,
                    "roles": [{"role": role.role} for role in role_profile_doc.roles],
                    "creation": role_profile_doc.creation,
                    "modified": role_profile_doc.modified
                }
            except frappe.DoesNotExistError:
                role_profile_data = None

        
        addresses = frappe.db.count("Address", 
            filters={"email_id": user.name},
            
        )
        
        response_data = {
            "success": True,
            "user": {
                "name": user.name,
                "email": user.email,
                "full_name": user.full_name,
                "user_image": user.user_image,
                "birth_date": user.birth_date,
                "phone": user.phone,
                # "roles": [role.role for role in user.roles],
                "role_profile_name": role_profile_name,
                # "role_profile": role_profile_data,
                "user_type": user.user_type,
                "enabled": user.enabled,
                
                
            },
            # "files": user_files
        }
        
        if customer:
            response_data["customer"] = customer

        response_data["user_files"] = user_files
        response_data["address_count"] = addresses or 0

        return response_data
    except Exception as e:
        frappe.log_error(f"Get current user error: {str(e)}")
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist(allow_guest=True)
@jwt_required()
def update_profile(full_name=None, phone=None, user_image=None, gender=None, date_of_birth=None,dob=None, 
                  social_security_number=None, address_line1=None, address_line2=None, city=None, 
                  state=None, zipcode=None, country=None, address_type="Personal", is_default=0,user_id=None,
                  custom_preferred_mode_of_payment=None):

    if dob:
        date_of_birth = dob

    """
    Update user profile, customer record, and address
    Uses standard Frappe authentication (session-based)
    """
    try:
        # Frappe automatically handles authentication with @frappe.whitelist()
        # frappe.session.user will be set to the authenticated user
        user_name = get_authenticated_user()
        if user_id:
            if is_administrator(frappe.session.user) or frappe.session.user == frappe.db.get_value("Customer", {"email_id": user_id}, "account_manager"):
                user_name = user_id
            else:
                frappe.throw("You don't have permission to update this user", frappe.PermissionError)
        if not user_name:
            frappe.local.response.http_status_code = 401
            return {"success": False, "message": "Authentication required"}
        user = frappe.get_doc("User", user_name)
        
        # Update user fields
        if full_name:
            user.full_name = full_name
            user.first_name = full_name.split()[0] if full_name else user.first_name
        
        if phone:
            user.phone = phone
        
        if user_image:
            user.user_image = user_image
            
        if date_of_birth:
            # Validate date format (YYYY-MM-DD) and update User's birth_date field
            from datetime import datetime
            try:
                datetime.strptime(date_of_birth, '%Y-%m-%d')
                user.birth_date = date_of_birth
                
            except ValueError:
                frappe.throw("Invalid date format. Please use YYYY-MM-DD format.")
        
        user.save(ignore_permissions=True)
        
        # Update customer record if exists
        # Try different ways to find the customer
        customer_data = frappe.get_all("Customer", 
            filters={"email_id": user.email},
            limit=1
        )
        
        # If not found by email, try by user field
        if not customer_data:
            customer_data = frappe.get_all("Customer", 
                filters={"user": user.name},
                limit=1
            )
        
        customer_info = None
        address_info = None
        
        if customer_data:
            customer = frappe.get_doc("Customer", customer_data[0].name)
            
            # Update basic customer info
            if full_name:
                customer.customer_name = full_name
            
            if phone:
                customer.mobile_no = phone
            
            if gender:
                customer.gender = gender
            
            if social_security_number:
                customer.tax_id = social_security_number
            
            if custom_preferred_mode_of_payment is not None:
                customer.custom_preferred_mode_of_payment = custom_preferred_mode_of_payment
            
            customer.save(ignore_permissions=True)
            
            # Handle address creation/update
            if any([address_line1, address_line2, city, state, zipcode, country]):
                address_result = create_or_update_customer_address(
                    customer=customer,
                    address_line1=address_line1,
                    address_line2=address_line2,
                    city=city,
                    state=state,
                    zipcode=zipcode,
                    country=country or "United States",
                    address_type=address_type,
                    phone=phone or customer.mobile_no,
                    email=user.email
                )
                
                # Check if address operation returned an error
                if isinstance(address_result, dict) and "error" in address_result:
                    return {
                        "success": False,
                        "message": f"Profile updated but address failed: {address_result['error']}"
                    }
                else:
                    address_info = address_result
            
            customer_info = {
                "name": customer.name,
                "customer_name": customer.customer_name,
                "customer_type": customer.customer_type,
                "email_id": customer.email_id,
                "mobile_no": customer.mobile_no,
                "gender": getattr(customer, 'gender', None),
                "tax_id": customer.tax_id,
                "is_seller": bool(getattr(customer, 'is_seller', 0)),
                "has_signed_agreement": bool(getattr(customer, 'has_signed_agreement', 0)),
                "is_questionnaire_filled": bool(getattr(customer, 'is_questionnaire_filled', 0)),
                "agreement_signed_date": getattr(customer, 'agreement_signed_date', None),
                "questionnaire_filled_date": getattr(customer, 'questionnaire_filled_date', None),
                "custom_preferred_mode_of_payment": getattr(customer, 'custom_preferred_mode_of_payment', None)
            }
        
        response_data = {
            "success": True,
            "message": "Profile updated successfully",
            "user": {
                "name": user.name,
                "email": user.email,
                "full_name": user.full_name,
                "phone": user.phone,
                "user_image": user.user_image,
                "birth_date": getattr(user, 'birth_date', None)
            }
        }
        
        if customer_info:
            response_data["customer"] = customer_info
            
        if address_info:
            response_data["address"] = address_info
        
        return response_data
    except Exception as e:
        # Use shorter error message to avoid cascading character limit issues
        error_type = type(e).__name__
        frappe.log_error(f"Profile update failed: {error_type}", "Profile Update Error")
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": f"Profile update failed: {error_type}"
        }

@frappe.whitelist(allow_guest=True)
@jwt_required()
def update_customer_flags(is_seller=None, has_signed_agreement=None, is_questionnaire_filled=None, user=None, password= None, customer_details=None):
    """
    Update customer flags (is_seller, has_signed_agreement, is_questionnaire_filled)
    Automatically authenticated via JWT decorator
    """
    try:
        
       
        user_name = get_authenticated_user()

        is_admin = is_administrator(user_name)
        
        if not is_admin and password:
            frappe.local.response.http_status_code = 401
            return {"success": False, "message": "Authentication failed. Only administrators can update passwords for other users."}
        
        if is_admin and password and user:
            # Admin is updating another user's password
            if not frappe.db.exists("User", user):
                frappe.local.response.http_status_code = 404
                return {"success": False, "message": "User to update not found."}
            user_doc = frappe.get_doc("User", user)
            user_doc.new_password = password
            user_doc.save(ignore_permissions=True)
            frappe.db.commit()
            return {
                "success": True,
                "message": "Password updated successfully"
            }
            
            user_name = user  # Switch context to the user whose password was changed
        elif password and not is_admin:
            # Non-admin user changing their own password
            user_doc = frappe.get_doc("User", user_name)
            user_doc.new_password = password
            user_doc.save(ignore_permissions=True)
            frappe.db.commit()
            
            return {
                "success": True,
                "message": "Password updated successfully"
            }
            
        if not user_name:
            frappe.local.response.http_status_code = 401
            return {"success": False, "message": "Authentication required"}
        
        user = frappe.get_doc("User", user_name)
        
        # Find customer record
        customer_data = frappe.get_all("Customer", 
            filters={"email_id": user.email},
            limit=1
        )
        
        if not customer_data:
            customer_data = frappe.get_all("Customer", 
                filters={"user": user.name},
                limit=1
            )
        
        if not customer_data:
            return {
                "success": False,
                "message": "Customer record not found"
            }
        
        customer = frappe.get_doc("Customer", customer_data[0].name)
        
        # Track what was updated
        updated_fields = []
        if customer_details:
            customer.customer_details = customer_details
            updated_fields.append("customer_details")
        # Update flags if provided
        if is_seller is not None:
            customer.is_seller = int(is_seller)
            updated_fields.append("is_seller")
            
            # Update user Role Profile when is_seller is true (but not for Administrators)
            if int(is_seller):
                try:
                    # Check if user is an Administrator using the imported function
                    is_admin = is_administrator(user.name)
                    
                    if not is_admin:
                        # Check if "Tradeline Seller" Role Profile exists
                        if frappe.db.exists("Role Profile", "Tradeline Seller"):
                            # Set the Role Profile for the user
                            frappe.db.set_value("User", user.name, "role_profile_name", "Tradeline Seller")
                            frappe.db.commit()
                            updated_fields.append("role_profile (Tradeline Seller)")
                        else:
                            frappe.log_error("Role Profile 'Tradeline Seller' not found", "Update Customer Flags")
                    else:
                        # Log that role profile was not set for admin user
                        frappe.logger().info(f"Role Profile not set for Administrator user: {user.name}")
                except Exception as role_error:
                    frappe.log_error(f"Failed to set Role Profile: {str(role_error)}", "Update Customer Flags")
        
        if has_signed_agreement is not None:
            customer.has_signed_agreement = int(has_signed_agreement)
            if has_signed_agreement:
                customer.agreement_signed_date = now_datetime()
            updated_fields.append("has_signed_agreement")
        
        if is_questionnaire_filled is not None:
            customer.is_questionnaire_filled = int(is_questionnaire_filled)
            if is_questionnaire_filled:
                customer.questionnaire_filled_date = now_datetime()
            updated_fields.append("is_questionnaire_filled")
        
        if not updated_fields:
            return {
                "success": False,
                "message": "No flags provided to update"
            }
        
        customer.save(ignore_permissions=True)
        
        return {
            "success": True,
            "message": f"Customer flags updated: {', '.join(updated_fields)}",
            "customer": {
                "name": customer.name,
                "customer_name": customer.customer_name,
                "is_seller": bool(customer.is_seller),
                "has_signed_agreement": bool(customer.has_signed_agreement),
                "is_questionnaire_filled": bool(customer.is_questionnaire_filled),
                "agreement_signed_date": customer.agreement_signed_date,
                "questionnaire_filled_date": customer.questionnaire_filled_date
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Update customer flags error: {str(e)}")
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_customer_status():
    """
    Get customer status flags and related information
    Automatically authenticated via JWT decorator
    """
    try:
        user_name = get_authenticated_user()
        if not user_name:
            frappe.local.response.http_status_code = 401
            return {"success": False, "message": "Authentication required"}
        
        user = frappe.get_doc("User", user_name)
        
        # Find customer record
        customer_data = frappe.get_all("Customer", 
            filters={"email_id": user.email},
            limit=1
        )
        
        if not customer_data:
            customer_data = frappe.get_all("Customer", 
                filters={"user": user.name},
                limit=1
            )
        
        if not customer_data:
            return {
                "success": False,
                "message": "Customer record not found"
            }
        
        customer = frappe.get_doc("Customer", customer_data[0].name)
        
        return {
            "success": True,
            "customer_status": {
                "name": customer.name,
                "customer_name": customer.customer_name,
                "customer_type": customer.customer_type,
                "is_seller": bool(getattr(customer, 'is_seller', 0)),
                "has_signed_agreement": bool(getattr(customer, 'has_signed_agreement', 0)),
                "is_questionnaire_filled": bool(getattr(customer, 'is_questionnaire_filled', 0)),
                "agreement_signed_date": getattr(customer, 'agreement_signed_date', None),
                "questionnaire_filled_date": getattr(customer, 'questionnaire_filled_date', None),
                "email_id": customer.email_id,
                "mobile_no": customer.mobile_no
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Get customer status error: {str(e)}")
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def test_auth():
    """
    Simple test function to verify authentication works
    """
    try:
        return {
            "success": True,
            "message": f"Authentication working for user: {frappe.session.user}",
            "user": frappe.session.user
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }

def create_or_update_customer_address(customer, address_line1=None, address_line2=None, 
                                    city=None, state=None, zipcode=None, country="United States",
                                    address_type="Personal", phone=None, email=None):
    """
    Create or update address for customer
    """
    try:
        # Check if customer already has a primary address
        existing_addresses = frappe.get_all("Address",
            filters={
                "link_doctype": "Customer",
                "link_name": customer.name,
                "address_type": address_type
            },
            fields=["name"],
            limit=1
        )
        
        # Prepare address data
        address_data = {
            "doctype": "Address",
            "address_type": address_type,
            "address_title": f"{customer.customer_name} - {address_type}",
            "email_id": email,
            "phone": phone,
            "is_primary_address": 1,
            "is_shipping_address": 1,
            "links": [{
                "link_doctype": "Customer",
                "link_name": customer.name
            }]
        }
        
        # Only update fields that are provided
        if address_line1:
            address_data["address_line1"] = address_line1
        if address_line2:
            address_data["address_line2"] = address_line2
        if city:
            address_data["city"] = city
        if state:
            address_data["state"] = state
        if zipcode:
            address_data["pincode"] = zipcode
        if country:
            address_data["country"] = country
        
        if existing_addresses:
            # Update existing address with retry logic for modification conflicts
            try:
                address = frappe.get_doc("Address", existing_addresses[0].name)
                
                for field, value in address_data.items():
                    if field not in ["doctype", "links"] and value is not None:
                        setattr(address, field, value)
                
                address.save(ignore_permissions=True)
            except frappe.exceptions.TimestampMismatchError:
                # Handle document modification conflict by reloading and retrying
                address = frappe.get_doc("Address", existing_addresses[0].name)
                address.reload()
                
                for field, value in address_data.items():
                    if field not in ["doctype", "links"] and value is not None:
                        setattr(address, field, value)
                
                address.save(ignore_permissions=True)
        else:
            # Create new address
            address = frappe.get_doc(address_data)
            address.insert(ignore_permissions=True)
        
        # Update customer's primary address link with retry logic
        try:
            customer.customer_primary_address = address.name
            customer.save(ignore_permissions=True)
        except frappe.exceptions.TimestampMismatchError:
            # Reload customer and retry
            customer.reload()
            customer.customer_primary_address = address.name
            customer.save(ignore_permissions=True)
        
        return {
            "name": address.name,
            "address_title": address.address_title,
            "address_type": address.address_type,
            "address_line1": getattr(address, 'address_line1', ''),
            "address_line2": getattr(address, 'address_line2', ''),
            "city": getattr(address, 'city', ''),
            "state": getattr(address, 'state', ''),
            "pincode": getattr(address, 'pincode', ''),
            "country": getattr(address, 'country', ''),
            "phone": getattr(address, 'phone', ''),
            "email_id": getattr(address, 'email_id', '')
        }
        
    except Exception as e:
        # Log error with short title to avoid character limit issues
        error_type = type(e).__name__
        frappe.log_error(f"Address error: {error_type} - {str(e)[:100]}", "Address Operation Failed")
        # Return error instead of raising to prevent cascading
        return {"error": f"Address update failed: {error_type}"}

# User Management APIs (Admin only)

@frappe.whitelist()
def create_customer_for_user(user_email):
    """
    Create customer record for existing user (Admin only)
    """
    try:
        if not frappe.has_permission("Customer", "create"):
            frappe.local.response.http_status_code = 403
            return {
                "success": False,
                "message": "Permission denied"
            }
        
        # Check if user exists
        if not frappe.db.exists("User", user_email):
            frappe.local.response.http_status_code = 404
            return {
                "success": False,
                "message": "User not found"
            }
        
        # Check if customer already exists
        existing_customer = frappe.get_all("Customer", 
            filters={"email_id": user_email},
            limit=1
        )
        
        if existing_customer:
            frappe.local.response.http_status_code = 409
            return {
                "success": False,
                "message": "Customer already exists for this user"
            }
        
        user = frappe.get_doc("User", user_email)
        
        # Create customer record
        customer = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": user.full_name or user.email,
            "customer_type": "Individual",
            "customer_group": "Individual",
            "territory": "All Territories",
            "email_id": user.email,
            "mobile_no": user.phone,
            "user": user.name,
            "account_manager": frappe.session.user if getattr(frappe.session, 'user', None) and frappe.session.user != 'Guest' else None,
            "is_primary_contact": 1
        })
        
        customer.insert(ignore_permissions=True)
        
        return {
            "success": True,
            "message": "Customer created successfully",
            "customer": {
                "name": customer.name,
                "customer_name": customer.customer_name,
                "customer_type": customer.customer_type,
                "email_id": customer.email_id,
                "mobile_no": customer.mobile_no
            }
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist(allow_guest=True)
@jwt_required()
@require_roles("Tradeline Broker", "System Manager")
def broker_create_client(email, full_name, phone=None, ssn=None,
                         address_line1=None, address_line2=None, city=None,
                         state=None, zipcode=None, country="United States",
                         role_profile_name=None):
    """Allow a broker (authenticated) to create a buyer client.

    - Password is auto-generated and returned in the response.
    - Required: email, full_name, ssn, address_line1, city, state, zipcode
    - Files can be uploaded via multipart form-data as fields: dl_front, dl_back, proof_of_residence
      (these should be file uploads in frappe.request.files)
    """
    try:
        # Basic validations
        if not email or not validate_email_address(email):
            frappe.local.response.http_status_code = 400
            return {"success": False, "message": "Valid email is required"}

        if frappe.db.exists("User", email):
            frappe.local.response.http_status_code = 409
            return {"success": False, "message": "User already exists"}

        if not full_name:
            frappe.local.response.http_status_code = 400
            return {"success": False, "message": "Full name is required"}

        # Required buyer fields
        if not ssn:
            frappe.local.response.http_status_code = 400
            return {"success": False, "message": "SSN (tax id) is required"}

        if not address_line1 or not city or not state or not zipcode:
            frappe.local.response.http_status_code = 400
            return {"success": False, "message": "Complete address (line1, city, state, zipcode) is required"}

        # Validate required file uploads
        files = frappe.request.files or {}
        
        # Check for required files
        dl_front = files.get("dl_front")
        proof_of_residence = files.get("proof_of_address") or files.get("proof_of_residence")
        social_security_number = files.get("social_security_number")
        
        if not dl_front:
            frappe.local.response.http_status_code = 400
            return {"success": False, "message": "Driver's license front (dl_front) file is required"}
        
        if not proof_of_residence:
            frappe.local.response.http_status_code = 400
            return {"success": False, "message": "Proof of residence (proof_of_residence) file is required"}
        
        if not social_security_number:
            frappe.local.response.http_status_code = 400
            return {"success": False, "message": "Social security number (social_security_number) file is required"}

        # Default role profile for broker-created clients is Tradeline Buyer
        role_profile_name = role_profile_name or "Tradeline Buyer"

        # Auto-generate password
        generated_password = random_string(12)

        # Determine roles
        roles_list = get_roles_from_role_profile(role_profile_name)

        # Create User (auto-verified)
        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "full_name": full_name,
            "first_name": full_name.split()[0] if full_name else email,
            "last_name": full_name.split()[1] if full_name and len(full_name.split()) > 1 else None,
            "enabled": 1,
            "role_profile_name": role_profile_name,
            "user_type": "Website User",
            "roles": roles_list,
            "email_verified": 1,  # broker-created accounts are treated as verified
            "email_verified_at": now_datetime(),
            "send_welcome_email": 0
        })

        user.new_password = generated_password
        if phone:
            user.phone = phone

        user.insert(ignore_permissions=True)
        frappe.db.commit()

        # Create Customer
        customer = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": full_name,
            "customer_type": "Individual",
            "customer_group": "Individual",
            "territory": "All Territories",
            "email_id": email,
            "mobile_no": phone,
            "user": user.name,
            "account_manager": frappe.session.user if getattr(frappe.session, 'user', None) and frappe.session.user != 'Guest' else None,
            "is_primary_contact": 1,
            "is_seller": 0,
            "is_buyer": 1,
            "is_broker": 0,
            "tax_id": ssn
        })

        customer = customer.insert(ignore_permissions=True)
        frappe.db.commit()

        # Create address
        address_result = create_or_update_customer_address(
            customer=customer,
            address_line1=address_line1,
            address_line2=address_line2,
            city=city,
            state=state,
            zipcode=zipcode,
            country=country,
            address_type="Personal",
            phone=phone,
            email=email
        )

        # Attach files if uploaded in request.files using same logic as upload_file
        attached_files = {}
        files = frappe.request.files or {}
        
        # Get allowed file names for validation
        from .files import get_allowed_file_names, validate_file
        allowed_file_names = get_allowed_file_names()
        
        for field_name in ("dl_front", "dl_back", "proof_of_address", "proof_of_residence"):
            file_obj = files.get(field_name)
            if file_obj:
                try:
                    # Validate file_name is allowed (same as upload_file)
                    if field_name not in allowed_file_names:
                        frappe.log_error(f"Invalid file_name '{field_name}' in broker_create_client for {email}. Only allowed: {', '.join(allowed_file_names)}", "File Upload Validation")
                        continue
                    
                    # Validate file using same logic as upload_file
                    validation_result = validate_file(file_obj)
                    if not validation_result["valid"]:
                        frappe.log_error(f"File validation failed for {field_name} in broker_create_client for {email}: {validation_result['message']}", "File Upload Validation")
                        continue
                    
                    # Generate filename using same logic as upload_file
                    original_ext = os.path.splitext(file_obj.filename)[1] if hasattr(file_obj, 'filename') else ""
                    base_filename = field_name
                    base_filename = secure_filename(base_filename)
                    
                    # Ensure the file has the correct extension
                    if original_ext and not base_filename.endswith(original_ext):
                        base_filename = f"{base_filename}{original_ext}"
                    
                    # Create custom filename: Customer_customer_name_field_name (consistent with upload_file format)
                    clean_customer_name = "".join(c for c in full_name if c.isalnum() or c in (' ', '-', '_')).replace(' ', '_')
                    custom_filename = f"Customer_{clean_customer_name}_{base_filename}"
                    custom_filename = secure_filename(custom_filename)
                    
                    content = file_obj.read()
                    
                    # Determine folder for private files based on allowed field name
                    from .files import create_or_get_folder
                    folder = create_or_get_folder(field_name, "Home")
                    frappe.logger().info(f"Using folder '{folder}' for private file '{field_name}' in broker_create_client")
                    
                    # Save file using same logic as upload_file
                    file_doc = save_file(
                        fname=custom_filename,
                        content=content,
                        dt="Customer",
                        dn=customer.name,
                        folder=folder,
                        is_private=1
                    )
                    
                    # Handle client_signature automation (same as upload_file)
                    if field_name == 'client_signature':
                        frappe.db.sql("update `tabCustomer` set is_questionnaire_filled = %s where email_id = %s", (1, email))
                    
                    attached_files[field_name] = {
                        "name": file_doc.name,
                        "file_name": file_doc.file_name,
                        "file_url": file_doc.file_url,
                        "file_size": file_doc.file_size,
                        "is_private": file_doc.is_private,
                        "content_hash": file_doc.content_hash
                    }
                    
                except Exception as file_err:
                    frappe.log_error(f"Failed to attach {field_name} for {email}: {str(file_err)}", "Broker Create Client File Upload")
                    # Continue processing other files instead of throwing error
                    attached_files[field_name] = {"error": str(file_err)}

        # Generate signature key for client signature
        signature_key = frappe.generate_hash(length=20)
        
        # Update user with signature key
        user.reset_password_key = signature_key  # Reusing reset_password_key field
        user.last_reset_password_key_generated_on = now_datetime()
        user.save(ignore_permissions=True)
        
        frappe.db.commit()
        
        # Send signature email to client
        try:
            send_client_signature_email(email, full_name, signature_key)
        except Exception as e:
            frappe.log_error(f"Failed to send signature email to {email}: {str(e)}", "Signature Email Error")

        return {
            "success": True,
            "message": "Client created successfully. Signature email sent to client.",
            "user": {
                "name": user.name,
                "email": user.email,
                "full_name": user.full_name,
                "password": generated_password
            },
            "customer": {
                "name": customer.name,
                "customer_name": customer.customer_name,
                "email_id": customer.email_id,
                "mobile_no": customer.mobile_no
            },
            "address": address_result,
            "files": attached_files,
            "signature_key": signature_key  # For testing purposes
        }

    except Exception as e:
        frappe.log_error(f"Broker create client error: {str(e)}")
        frappe.local.response.http_status_code = 500
        return {"success": False, "message": str(e)}

@frappe.whitelist(allow_guest=True)
@jwt_required()
@require_roles("System Manager", "Administrator")
def get_users(limit=20, start=0, search=None):
    """
    Get list of users with customer information (Admin only)
    Requires System Manager or Administrator role
    """
    try:
        filters = {}
        if search:
            filters["email"] = ["like", f"%{search}%"]
        
        users = frappe.get_all("User", 
            filters=filters,
            fields=["name", "email", "full_name", "enabled", "user_type", "creation", "phone"],
            limit=limit,
            start=start,
            order_by="creation desc"
        )
        
        # Add customer information for each user
        for user in users:
            customer_data = frappe.get_all("Customer", 
                filters={"user": user.name},
                fields=["name", "customer_name", "customer_type", "email_id", "mobile_no"],
                limit=1
            )
            
            if customer_data:
                user["customer"] = customer_data[0]
            else:
                user["customer"] = None
        
        return {
            "success": True,
            "users": users
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }
    
@frappe.whitelist(allow_guest=True)
@jwt_required()
@require_roles("Tradeline Broker", "Administrator", "System Manager")
def get_broker_customers(limit=50, start=0, search=None):
    """Return customers where account_manager is the logged-in broker"""
    try:
        broker = get_authenticated_user()
        if not broker or broker == "Guest":
            frappe.local.response.http_status_code = 401
            return {"success": False, "message": "Authentication required"}

        # Convert limit and start to integers with validation
        try:
            limit = int(limit) if limit else 50
            start = int(start) if start else 0
        except (ValueError, TypeError):
            frappe.local.response.http_status_code = 400
            return {"success": False, "message": "Invalid pagination parameters. 'limit' and 'start' must be valid integers."}
        
        filters = {"account_manager": broker}
        if search:
            filters["customer_name"] = ["like", f"%{search}%"]

        # Get total count for pagination
        total_count = frappe.db.count("Customer", filters)

        customers = frappe.get_all("Customer",
            filters=filters,
            fields=["name", "customer_name", "email_id", "mobile_no",  "creation"],
            limit=limit,
            start=start,
            order_by="creation desc"
        )

        # Calculate pagination
        current_page = (start // limit) + 1 if limit > 0 else 1
        total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
        has_next = (start + limit) < total_count
        has_previous = start > 0

        return {
            "success": True,
            "customers": customers,
            "pagination": {
                "current_page": current_page,
                "total_pages": total_pages,
                "limit": limit,
                "start": start,
                "has_next": has_next,
                "has_previous": has_previous,
                "total_records": total_count
            }
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {"success": False, "message": str(e)}

@frappe.whitelist()
def update_user(user_id, full_name=None, enabled=None, roles=None):
    """
    Update user (Admin only)
    """
    try:
        if not frappe.has_permission("User", "write"):
            frappe.local.response.http_status_code = 403
            return {
                "success": False,
                "message": "Permission denied"
            }
        
        user = frappe.get_doc("User", user_id)
        
        if full_name:
            user.full_name = full_name
        
        if enabled is not None:
            user.enabled = enabled
        
        if roles:
            user.roles = []
            for role in roles:
                user.append("roles", {"role": role})
        
        user.save(ignore_permissions=True)
        
        return {
            "success": True,
            "message": "User updated successfully"
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def delete_user(user_id):
    """
    Delete user (Admin only)
    """
    try:
        if not frappe.has_permission("User", "delete"):
            frappe.local.response.http_status_code = 403
            return {
                "success": False,
                "message": "Permission denied"
            }
        
        frappe.delete_doc("User", user_id)
        
        return {
            "success": True,
            "message": "User deleted successfully"
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist(allow_guest=True)
@jwt_required()
def refresh_token():
    """
    Refresh JWT token for authenticated user
    Automatically authenticated via JWT decorator
    """
    try:
        # Generate new JWT token
        user_name = get_authenticated_user()
        if not user_name:
            frappe.local.response.http_status_code = 401
            return {"success": False, "message": "Authentication required"}
        jwt_token = generate_jwt_token(user_name)
        
        return {
            "success": True,
            "message": "Token refreshed successfully",
            "authorization_token": f"Bearer {jwt_token}",
            "token_type": "Bearer",
            "expires_in": 86400  # 24 hours in seconds
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def validate_token():
    """
    Validate current JWT token and return user info
    """
    try:
        user_name = validate_authorization_header()
        
        if not user_name:
            frappe.local.response.http_status_code = 401
            return {
                "success": False,
                "message": "Invalid or expired token"
            }
        
        user = frappe.get_doc("User", user_name)
        
        return {
            "success": True,
            "message": "Token is valid",
            "user": {
                "name": user.name,
                "email": user.email,
                "full_name": user.full_name,
                "roles": [role.role for role in user.roles]
            }
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

# Example endpoints demonstrating decorator usage

@frappe.whitelist(allow_guest=True)
@jwt_required()
def protected_endpoint():
    """
    Example protected endpoint that requires authentication
    """
    user_name = get_authenticated_user()
    if not user_name:
        frappe.local.response.http_status_code = 401
        return {"success": False, "message": "Authentication required"}
    return {
        "success": True,
        "message": f"Hello {user_name}!",
        "user": user_name,
        "roles": frappe.get_roles(user_name)
    }

@frappe.whitelist(allow_guest=True)
@jwt_required(allow_guest=True)
def optional_auth_endpoint():
    """
    Example endpoint that works with or without authentication
    """
    user_name = get_authenticated_user()
    if user_name:
        return {
            "success": True,
            "message": f"Welcome back, {user_name}!",
            "authenticated": True,
            "user": user_name
        }
    else:
        return {
            "success": True,
            "message": "Hello Guest! You can access this without authentication.",
            "authenticated": False,
            "user": "Guest"
        }

@frappe.whitelist(allow_guest=True)
@jwt_required()
@require_roles("System Manager", "Administrator")
def admin_only_endpoint():
    """
    Example endpoint that requires admin roles
    """
    user_name = get_authenticated_user()
    if not user_name:
        frappe.local.response.http_status_code = 401
        return {"success": False, "message": "Authentication required"}
    return {
        "success": True,
        "message": f"Admin access granted to {user_name}",
        "user": user_name,
        "roles": frappe.get_roles(user_name)
    }

# Example endpoints demonstrating JWT decorators
@frappe.whitelist(allow_guest=True)
def public_endpoint():
    """Public endpoint - no authentication required"""
    return {
        "success": True,
        "message": "This is a public endpoint",
        "user": frappe.session.user if frappe.session.user != "Guest" else "Anonymous"
    }

@frappe.whitelist(allow_guest=True)
@jwt_required()
def protected_endpoint():
    """Protected endpoint - requires valid JWT token"""
    user_name = get_authenticated_user()
    if not user_name:
        frappe.local.response.http_status_code = 401
        return {"success": False, "message": "Authentication required"}
    return {
        "success": True,
        "message": "This is a protected endpoint",
        "user": user_name
    }

@frappe.whitelist(allow_guest=True)
@jwt_required(allow_guest=True)
def optional_auth_endpoint():
    """Optional auth endpoint - works with or without JWT token"""
    user_name = get_authenticated_user()
    if user_name:
        return {
            "success": True,
            "message": f"Hello authenticated user {user_name}",
            "user": user_name
        }
    else:
        return {
            "success": True,
            "message": "Hello anonymous user",
            "user": "Guest"
        }

# Email Verification Endpoints

@frappe.whitelist(allow_guest=True)
def verify_email(token):
    """Verify email address using verification token"""
    try:
        if not token:
            frappe.local.response.http_status_code = 400
            error_message = f"""
            <div style="text-align: center; padding: 20px;">
                <div style="margin-bottom: 30px;">
                    <img src="{frappe.utils.get_url()}/assets/rockettradeline/logo.png" alt="Rocket Tradeline" style="max-height: 60px; max-width: 200px;" />
                </div>
                <div style="width: 60px; height: 60px; background-color: #ef4444; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 20px;">
                    <span style="color: white; font-size: 30px; font-weight: bold;">✗</span>
                </div>
                <h1 style="color: #1f2937; font-size: 24px; margin-bottom: 15px;">Invalid Verification Link</h1>
                <p style="color: #6b7280; font-size: 16px; line-height: 1.6; margin-bottom: 30px;">
                    The verification link appears to be incomplete or corrupted. Please check your email for the correct verification link.
                </p>
                <a href="https://www.rockettradeline.com" style="background-color: #17B26A; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">Go to Homepage</a>
            </div>
            """
            frappe.respond_as_web_page("Invalid Verification Link - Rocket Tradeline", error_message, success=False)
            return
        
        # Find user with this verification token
        users = frappe.get_all("User", 
            filters={"email_verification_token": token},
            fields=["name", "email", "email_verification_sent_at"]
        )
        
        if not users:
            frappe.local.response.http_status_code = 400
            error_message = f"""
            <div style="text-align: center; padding: 20px;">
                <div style="margin-bottom: 30px;">
                    <img src="{frappe.utils.get_url()}/assets/rockettradeline/logo.png" alt="Rocket Tradeline" style="max-height: 60px; max-width: 200px;" />
                </div>
                <div style="width: 60px; height: 60px; background-color: #ef4444; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 20px;">
                    <span style="color: white; font-size: 30px; font-weight: bold;">✗</span>
                </div>
                <h1 style="color: #1f2937; font-size: 24px; margin-bottom: 15px;">Invalid Verification Token</h1>
                <p style="color: #6b7280; font-size: 16px; line-height: 1.6; margin-bottom: 30px;">
                    The verification link you clicked is invalid or has already been used. Please check your email for the correct link or request a new verification email.
                </p>
                <a href="https://www.rockettradeline.com" style="background-color: #17B26A; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">Go to Homepage</a>
            </div>
            """
            frappe.respond_as_web_page("Invalid Verification Token - Rocket Tradeline", error_message, success=False)
            return
        
        user_data = users[0]
        user_doc = frappe.get_doc("User", user_data.name)
        
        # Check if token has expired (24 hours from sent_at)
        if user_data.email_verification_sent_at:
            expiry_time = user_data.email_verification_sent_at + timedelta(hours=24)
            if now_datetime() > expiry_time:
                frappe.local.response.http_status_code = 400
                expired_message = f"""
                <div style="text-align: center; padding: 20px;">
                    <div style="margin-bottom: 30px;">
                        <img src="{frappe.utils.get_url()}/assets/rockettradeline/images/logo.png" alt="Rocket Tradeline" style="max-height: 60px; max-width: 200px;" />
                    </div>
                    <div style="width: 60px; height: 60px; background-color: #f59e0b; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 20px;">
                        <span style="color: white; font-size: 30px; font-weight: bold;">⚠</span>
                    </div>
                    <h1 style="color: #1f2937; font-size: 24px; margin-bottom: 15px;">Verification Link Expired</h1>
                    <p style="color: #6b7280; font-size: 16px; line-height: 1.6; margin-bottom: 30px;">
                        This verification link has expired. For security reasons, verification links are only valid for 24 hours. Please sign up again or contact support for assistance.
                    </p>
                    <a href="https://www.rockettradeline.com" style="background-color: #17B26A; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">Go to Homepage</a>
                </div>
                """
                frappe.respond_as_web_page("Verification Link Expired - Rocket Tradeline", expired_message, success=False)
                return
        
        # Mark email as verified
        user_doc.db_set("email_verified", 1, commit=True)
        user_doc.db_set("email_verification_token", None, commit=True)
        user_doc.db_set("email_verified_at", now_datetime(), commit=True)
        
        # Return HTML success page with login redirect
        success_message = f"""
        <div style="text-align: center; padding: 20px;">
            <div style="margin-bottom: 30px;">
                <img src="{frappe.utils.get_url()}/assets/rockettradeline/logo.png" alt="Rocket Tradeline" style="max-height: 60px; max-width: 200px;" />
            </div>
            <div style="width: 60px; height: 60px; background-color: #17B26A; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 20px;">
                <span style="color: white; font-size: 30px; font-weight: bold;">✓</span>
            </div>
            <h1 style="color: #1f2937; font-size: 24px; margin-bottom: 15px;">Your Account Has Been Verified!</h1>
            <p style="color: #6b7280; font-size: 16px; line-height: 1.6; margin-bottom: 30px;">
                Congratulations! Your email address has been successfully verified. You can now access your Rocket Tradeline account and start buying and selling tradelines.
            </p>
            <a href="https://www.rockettradeline.com/login" style="background-color: #17B26A; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">Click Here to Login</a>
        </div>
        """
        from .marketing import send_welcome_email
        try:
            send_welcome_email(user_doc.email, user_doc.full_name)
        except Exception as e:
            frappe.log_error(f"Failed to send welcome email to {user_doc.email}: {str(e)}", "Welcome Email Error")
        frappe.respond_as_web_page("Email Verified - Rocket Tradeline", success_message, success=True)
        return
        
    except Exception as e:
        frappe.log_error(f"Email verification error: {str(e)}")
        frappe.local.response.http_status_code = 500
        error_message = f"""
        <div style="text-align: center; padding: 20px;">
            <div style="margin-bottom: 30px;">
                <img src="{frappe.utils.get_url()}/assets/rockettradeline/images/logo.png" alt="Rocket Tradeline" style="max-height: 60px; max-width: 200px;" />
            </div>
            <div style="width: 60px; height: 60px; background-color: #ef4444; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 20px;">
                <span style="color: white; font-size: 30px; font-weight: bold;">✗</span>
            </div>
            <h1 style="color: #1f2937; font-size: 24px; margin-bottom: 15px;">Verification Error</h1>
            <p style="color: #6b7280; font-size: 16px; line-height: 1.6; margin-bottom: 30px;">
                An error occurred during email verification. Please try again or contact support if the problem persists.
            </p>
            <a href="https://www.rockettradeline.com" style="background-color: #17B26A; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">Go to Homepage</a>
        </div>
        """
        frappe.respond_as_web_page("Verification Error - Rocket Tradeline", error_message, success=False)
        return

@frappe.whitelist(allow_guest=True)
def resend_verification_email(email):
    """Resend verification email"""
    try:
        if not email or not validate_email_address(email):
            frappe.local.response.http_status_code = 400
            return {
                "success": False,
                "message": "Valid email address is required"
            }
        
        # Check if user exists
        if not frappe.db.exists("User", email):
            frappe.local.response.http_status_code = 404
            return {
                "success": False,
                "message": "User not found"
            }
        
        user_doc = frappe.get_doc("User", email)
        
        # Check if email is already verified
        if getattr(user_doc, 'email_verified', False):
            frappe.local.response.http_status_code = 400
            return {
                "success": False,
                "message": "Email is already verified"
            }
        
        # Generate new verification token
        verification_token = generate_verification_token(email)
        if not verification_token:
            frappe.local.response.http_status_code = 500
            return {
                "success": False,
                "message": "Failed to generate verification token"
            }
        
        # Send verification email
        email_sent = send_verification_email(email, user_doc.full_name, verification_token)
        
        return {
            "success": True,
            "message": "Verification email sent successfully! Please check your inbox.",
            "email_sent": email_sent
        }
        
    except Exception as e:
        frappe.log_error(f"Resend verification email error: {str(e)}")
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": "An error occurred while sending verification email. Please try again."
        }

@frappe.whitelist(allow_guest=True)
def get_verification_token_for_testing(email):
    """Get verification token for testing purposes - REMOVE IN PRODUCTION"""
    try:
        if not email:
            return {
                "success": False,
                "message": "Email is required"
            }
            
        # Check if user exists
        if not frappe.db.exists("User", email):
            return {
                "success": False,
                "message": "User not found"
            }
            
        # Get verification token
        token = frappe.db.get_value("User", email, "email_verification_token")
        sent_at = frappe.db.get_value("User", email, "email_verification_sent_at")
        
        if not token:
            return {
                "success": False,
                "message": "No verification token found for this user"
            }
            
        # Create verification link
        site_url = frappe.utils.get_url()
        verification_link = f"{site_url}/api/method/rockettradeline.api.auth.verify_email?token={token}"
        
        return {
            "success": True,
            "email": email,
            "verification_token": token,
            "verification_link": verification_link,
            "sent_at": sent_at,
            "note": "This endpoint is for testing only and should be removed in production"
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting verification token for {email}: {str(e)}")
        return {
            "success": False,
            "message": "An error occurred while retrieving verification token"
        }

@frappe.whitelist(allow_guest=True)
def get_profile():
    """
    Get user profile information - JWT protected endpoint
    Manual JWT validation without decorator to bypass Frappe auth issues
    """
    try:
        # Manual JWT validation using custom header to avoid Frappe interference
        auth_header = frappe.get_request_header("X-Authorization") or frappe.get_request_header("Authorization")
        
        if not auth_header:
            frappe.local.response.http_status_code = 401
            return {
                "success": False,
                "message": "No valid Authorization token provided. Use X-Authorization header or Authorization header."
            }
        
        # Handle both "Bearer token" and just "token" formats
        if auth_header.startswith("Bearer "):
            jwt_token = auth_header.replace("Bearer ", "")
        else:
            jwt_token = auth_header
        payload = validate_jwt_token(jwt_token)
        
        if not payload:
            frappe.local.response.http_status_code = 401
            return {
                "success": False,
                "message": "Invalid or expired token"
            }
        
        # Get user information from payload
        user_email = payload.get("user_id") or payload.get("email")
        if not user_email:
            frappe.local.response.http_status_code = 401
            return {
                "success": False,
                "message": "Invalid token payload"
            }
        
        # Get user document
        user = frappe.get_doc("User", user_email)
        
        # Get full customer document with child tables if exists
        customer = None
        customer_list = frappe.get_all("Customer", 
            filters={"user": user.name},
            fields=["name"],
            limit=1
        )
        
        if customer_list:
            # Get the complete customer document with all child tables
            customer_doc = frappe.get_doc("Customer", customer_list[0].name)
            
            # Convert to dict to include child tables
            customer = customer_doc.as_dict()
            
            # Remove system fields that aren't needed in API response
            system_fields = ['docstatus', 'idx', 'owner', 'modified_by', 'creation', 'modified']
            for field in system_fields:
                customer.pop(field, None)
        
        # Get role profile information
        role_profile_name = getattr(user, 'role_profile_name', None)
        role_profile_data = None
        
        if role_profile_name:
            try:
                role_profile_doc = frappe.get_doc("Role Profile", role_profile_name)
                role_profile_data = {
                    "name": role_profile_doc.name,
                    "role_profile": role_profile_doc.role_profile,
                    "roles": [{"role": role.role} for role in role_profile_doc.roles],
                    "creation": role_profile_doc.creation,
                    "modified": role_profile_doc.modified
                }
            except frappe.DoesNotExistError:
                role_profile_data = None

        response_data = {
            "success": True,
            "user": {
                "name": user.name,
                "email": user.email,
                "full_name": user.full_name,
                "user_image": user.user_image,
                "phone": user.phone,
                "roles": [role.role for role in user.roles],
                "role_profile_name": role_profile_name,
                "role_profile": role_profile_data,
                "user_type": user.user_type,
                "enabled": user.enabled,
                "creation": user.creation.strftime("%Y-%m-%d %H:%M:%S") if user.creation else None
            }
        }
        
        if customer:
            response_data["customer"] = customer
        
        return response_data
    except Exception as e:
        frappe.log_error(f"Profile fetch error: {str(e)}")
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist(allow_guest=True)
def test_jwt_validation():
    """Test JWT token validation to debug authentication issues"""
    try:
        # Get Authorization header - use custom header to avoid Frappe interference
        auth_header = frappe.get_request_header("X-Authorization") or frappe.get_request_header("Authorization")
        
        if not auth_header:
            return {
                "success": False,
                "message": "No Authorization header provided. Use X-Authorization or Authorization header.",
                "debug": {
                    "headers": dict(frappe.local.request.headers) if frappe.local.request else "No request"
                }
            }
        
        # Handle both "Bearer token" and just "token" formats
        if auth_header.startswith("Bearer "):
            jwt_token = auth_header.replace("Bearer ", "")
        else:
            jwt_token = auth_header
        
        # Test JWT validation
        payload = validate_jwt_token(jwt_token)
        
        if payload:
            return {
                "success": True,
                "message": "JWT token is valid",
                "payload": payload,
                "current_user": frappe.session.user
            }
        else:
            return {
                "success": False,
                "message": "JWT token validation failed",
                "token_preview": jwt_token[:20] + "..." if len(jwt_token) > 20 else jwt_token
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"Error testing JWT: {str(e)}",
            "error_type": type(e).__name__
        }

@frappe.whitelist(allow_guest=True)
def test_customer_data(user_email="philmaxsnr@gmail.com"):
    """Test endpoint to check customer data for debugging"""
    try:
        # Check customers by email
        customers_by_email = frappe.get_all("Customer", 
            filters={"email_id": user_email},
            fields=["name", "customer_name", "email_id", "mobile_no", "customer_type"],
            limit=5
        )
        
        # Get all customers to see what exists
        all_customers = frappe.get_all("Customer", 
            fields=["name", "customer_name", "email_id", "mobile_no"],
            limit=10
        )
        
        # Get Customer doctype meta to see available fields
        customer_meta = frappe.get_meta("Customer")
        available_fields = [field.fieldname for field in customer_meta.fields if field.fieldtype not in ["Section Break", "Column Break", "HTML"]]
        
        # If we find a customer, get the full document
        customer_doc = None
        if customers_by_email:
            customer_doc = frappe.get_doc("Customer", customers_by_email[0].name).as_dict()
            # Remove system fields
            system_fields = ['docstatus', 'idx', 'owner', 'modified_by', 'creation', 'modified']
            for field in system_fields:
                customer_doc.pop(field, None)
        
        return {
            "success": True,
            "customers_by_email": customers_by_email,
            "all_customers": all_customers,
            "available_fields": available_fields,
            "customer_document": customer_doc
        }
        
    except Exception as e:
        frappe.log_error(f"Customer data test error: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist(allow_guest=True)
def test_send_verification_email_simple(email):
    """Simple test of send_verification_email function - FOR TESTING ONLY"""
    try:
        if not email:
            return {
                "success": False,
                "message": "Email is required"
            }
        
        # Check if user exists
        if not frappe.db.exists("User", email):
            return {
                "success": False,
                "message": "User not found"
            }
        
        # Get user details
        user_doc = frappe.get_doc("User", email)
        
        # Use existing token or generate new one
        existing_token = frappe.db.get_value("User", email, "email_verification_token")
        if existing_token:
            test_token = existing_token
        else:
            test_token = generate_verification_token(email)
        
        if not test_token:
            return {
                "success": False,
                "message": "Failed to get or generate verification token"
            }
        
        # Test the send_verification_email function with detailed logging
        print(f"Testing send_verification_email for {email}")
        try:
            email_sent = send_verification_email(email, user_doc.full_name, test_token)
            print(f"send_verification_email returned: {email_sent}")
        except Exception as e:
            print(f"send_verification_email threw exception: {str(e)}")
            email_sent = False
        
        # Create verification link for reference
        site_url = frappe.utils.get_url()
        verification_link = f"{site_url}/api/method/rockettradeline.api.auth.verify_email?token={test_token}"
        
        # Test frappe.sendmail with simple message first
        print("Testing frappe.sendmail with simple message...")
        try:
            frappe.sendmail(
                recipients=[email],
                subject=f"Test Simple Email - {frappe.local.site}",
                message=f"Hello {user_doc.full_name}, this is a simple test email.",
                delayed=False
            )
            print("Simple frappe.sendmail call succeeded!")
            simple_sendmail_result = True
        except Exception as e:
            print(f"Simple frappe.sendmail failed: {str(e)}")
            simple_sendmail_result = False
        
        # Test frappe.sendmail directly with template
        print("Testing frappe.sendmail with template...")
        try:
            frappe.sendmail(
                recipients=[email],
                subject=f"Verify Your Email Address - {frappe.local.site}",
                template="Email Verification",
                args={
                    "site_name": frappe.local.site,
                    "full_name": user_doc.full_name,
                    "verification_link": verification_link
                },
                header=["Verify Your Email Address", "green"],
                delayed=False,
                retry=3
            )
            print("Template frappe.sendmail call succeeded!")
            template_sendmail_result = True
        except Exception as e:
            print(f"Template frappe.sendmail failed: {str(e)}")
            template_sendmail_result = False
        
        # Basic email configuration check
        email_accounts = frappe.get_all('Email Account', 
            filters={'enable_outgoing': 1, 'default_outgoing': 1},
            fields=['name', 'email_id']
        )
        
        has_email_config = len(email_accounts) > 0
        
        return {
            "success": True,
            "function_result": email_sent,
            "simple_sendmail_result": simple_sendmail_result,
            "template_sendmail_result": template_sendmail_result,
            "user_email": email,
            "user_name": user_doc.full_name,
            "token_used": test_token[:50] + "..." if test_token else None,
            "verification_link": verification_link,
            "has_email_config": has_email_config,
            "email_account": email_accounts[0]['name'] if email_accounts else None,
            "note": "This tests send_verification_email function, simple sendmail, and template sendmail"
        }
        
    except Exception as e:
        frappe.log_error(f"Test email sending error: {str(e)}")
        import traceback
        return {
            "success": False,
            "message": f"Error testing email: {str(e)}",
            "traceback": traceback.format_exc()
        }

@frappe.whitelist(allow_guest=True)
@jwt_required()
def test_permissions():
    # Implement permission testing logic here
    doc = frappe.get_doc('User Task', '1')
    doc.title = 'Test'
    doc.save()


@frappe.whitelist(allow_guest=True)
def send_reset_password_link(email):
    """
    Send reset password link to user's email
    
    Args:
        email (str): User's email address
        
    Returns:
        dict: Success/failure response with message
    """
    try:
        # Validate email format
        if not email:
            return {
                "success": False,
                "message": "Email address is required"
            }
        
        if not validate_email_address(email):
            return {
                "success": False,
                "message": "Invalid email address format"
            }
        
        # Check if user exists
        user_exists = frappe.db.exists("User", {"email": email, "enabled": 1})
        if not user_exists:
            # For security, don't reveal if user exists or not
            return {
                "success": True,
                "message": "If the email address is registered, you will receive a password reset link shortly."
            }
        
        # Get user document
        user_doc = frappe.get_doc("User", email)
        
        # Generate reset password key
        reset_key = frappe.generate_hash(length=20)
        
        # Update user with reset key and expiry
        user_doc.reset_password_key = reset_key
        user_doc.last_reset_password_key_generated_on = now_datetime()
        user_doc.save(ignore_permissions=True)
        frappe.db.commit()
        
        # Create reset password link
        reset_link = f"https://www.rockettradeline.com/reset-password?key={reset_key}"
        
        # Get user's full name
        full_name = user_doc.full_name or user_doc.first_name or email.split('@')[0]
        
        # Try to use Email Template Custom first
        try:
            # Check if Email Template Custom exists and template is available
            if frappe.db.exists('DocType', 'Email Template Custom') and frappe.db.exists('Email Template Custom', 'Password Reset'):
                # Use the Email Template Custom system
                from rockettradeline.utils.email_templates import send_email_from_template
                
                # Prepare context for template
                context = {
                    'full_name': full_name,
                    'site_name': 'RocketTradeline',
                    'reset_link': reset_link,
                    'recipient_email': email
                }
                
                # Send email using template
                result = send_email_from_template('Password Reset', email, context)
                
                if result.get('success'):
                    frappe.logger().info(f"Password reset email sent using template to {email}")
                    return {
                        "success": True,
                        "message": "If the email address is registered, you will receive a password reset link shortly."
                    }
                else:
                    frappe.log_error(f"Template password reset email failed for {email}: {result.get('error')}", "Template Email Error")
                    # Fall back to hardcoded email below
            else:
                frappe.logger().info("Email Template Custom not available for password reset, using fallback method")
        
        except Exception as template_error:
            frappe.log_error(f"Template password reset email system failed for {email}: {str(template_error)}", "Template Email System Error")
            # Fall back to hardcoded email below
        
        # Fallback: Send email using hardcoded template (original method)
        # Get consistent email header and footer
        email_header = get_email_header()
        email_footer = get_email_footer(email)
        
        # Prepare email content
        subject = "Password Reset Request - RocketTradeline"
        
        message = f"""{email_header}
        <h3 style="color: #374151; margin: 0 0 20px 0;">Password Reset Request</h3>
        <p style="color: #374151; font-size: 16px; margin: 0 0 10px 0;">Hello {full_name},</p>
        
        <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0 0 25px 0;">
            We received a request to reset your password for your RocketTradeline account. If you made this request, click the button below to reset your password.
        </p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_link}" 
               style="background-color: #17B26A; color: white; padding: 14px 28px; text-decoration: none; 
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
        
        <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 25px 0 0 0;">
            If the button above doesn't work, you can copy and paste this link into your browser:
        </p>
        
        <div style="background-color: #f3f4f6; padding: 15px; border-radius: 6px; margin: 15px 0; word-break: break-all;">
            <p style="margin: 0; color: #374151; font-family: monospace; font-size: 14px;">
                {reset_link}
            </p>
        </div>
        
        <div style="background-color: #fef2f2; border: 1px solid #fecaca; padding: 15px; border-radius: 6px; margin: 25px 0;">
            <p style="margin: 0; color: #DC2626; font-weight: 600; font-size: 14px;">
                ⚠️ Important: If you did not request a password reset, please contact our support team immediately.
            </p>
        </div>
        
        <p style="color: #6b7280; margin: 25px 0 0 0; font-size: 16px;">
            If you need assistance, please contact our support team at info@rockettradeline.com
        </p>
        {email_footer}"""
        
        # Prepare template parameters
        template_params = {
            "full_name": full_name,
            "site_name": frappe.local.site,
            "reset_link": reset_link
        }
        
        # Send email using template
        from rockettradeline.rockettradeline.doctype.email_template_custom.email_template_custom import send_email_template
        
        send_email_template(
            template_name="Password Reset",
            recipients=[email],
            parameters=template_params
        )
        
        # Log the password reset request
        frappe.logger().info(f"Password reset link sent to {email}")
        
        return {
            "success": True,
            "message": "If the email address is registered, you will receive a password reset link shortly."
        }
        
    except Exception as e:
        frappe.log_error(f"Password reset link generation failed: {str(e)}", "Password Reset Error")
        return {
            "success": False,
            "message": "An error occurred while processing your request. Please try again later."
        }


@frappe.whitelist(allow_guest=True)
def validate_reset_password_key(key):
    """
    Validate reset password key
    
    Args:
        key (str): Reset password key
        
    Returns:
        dict: Validation result with user email if valid
    """
    try:
        if not key:
            return {
                "success": False,
                "message": "Reset key is required"
            }
        
        # Find user with this reset key
        user_data = frappe.db.get_value(
            "User",
            {"reset_password_key": key, "enabled": 1},
            ["email", "last_reset_password_key_generated_on"],
            as_dict=True
        )
        
        if not user_data:
            return {
                "success": False,
                "message": "Invalid or expired reset key"
            }
        
        # Check if key has expired (24 hours)
        if user_data.last_reset_password_key_generated_on:
            key_generated_time = user_data.last_reset_password_key_generated_on
            expiry_time = key_generated_time + timedelta(hours=24)
            
            if now_datetime() > expiry_time:
                return {
                    "success": False,
                    "message": "Reset key has expired. Please request a new one."
                }
        
        return {
            "success": True,
            "message": "Reset key is valid",
            "email": user_data.email
        }
        
    except Exception as e:
        frappe.log_error(f"Reset key validation failed: {str(e)}", "Reset Key Validation Error")
        return {
            "success": False,
            "message": "An error occurred while validating the reset key"
        }


@frappe.whitelist(allow_guest=True)
def reset_password_with_key(key, new_password):
    """
    Reset password using reset key
    
    Args:
        key (str): Reset password key
        new_password (str): New password
        
    Returns:
        dict: Success/failure response
    """
    try:
        if not key or not new_password:
            return {
                "success": False,
                "message": "Reset key and new password are required"
            }
        
        # Validate the reset key first
        validation_result = validate_reset_password_key(key)
        if not validation_result.get("success"):
            return validation_result
        
        email = validation_result.get("email")
        
        # Validate password strength
        if len(new_password) < 8:
            return {
                "success": False,
                "message": "Password must be at least 8 characters long"
            }
        
        # Get user document
        user_doc = frappe.get_doc("User", email)
        
        # Update password
        user_doc.new_password = new_password
        
        # Clear reset key to prevent reuse
        user_doc.reset_password_key = None
        user_doc.last_reset_password_key_generated_on = None
        
        # Save user
        user_doc.save(ignore_permissions=True)
        frappe.db.commit()
        
        # Log successful password reset
        frappe.logger().info(f"Password successfully reset for user: {email}")
        
        return {
            "success": True,
            "message": "Password has been reset successfully. You can now log in with your new password."
        }
        
    except Exception as e:
        frappe.log_error(f"Password reset failed: {str(e)}", "Password Reset Error")
        return {
            "success": False,
            "message": "An error occurred while resetting your password. Please try again."
        }


def send_client_signature_email(client_email, full_name, signature_key):
    """
    Send signature request email to client
    
    Args:
        client_email (str): Client's email address
        full_name (str): Client's full name
        signature_key (str): Unique signature key
    """
    try:
        # Create signature link
        signature_link = f"https://www.rockettradeline.com/client-signature?key={signature_key}"
        
        # Get consistent email header and footer
        email_header = get_email_header()
        email_footer = get_email_footer(client_email)
        
        # Prepare email content
        subject = "Complete Your Account Setup - Signature Required"
        
        message = f"""{email_header}
        <h3 style="color: #374151; margin: 0 0 20px 0;">📝 Complete Your Account Setup</h3>
        <p style="color: #374151; font-size: 16px; margin: 0 0 10px 0;">Hello {full_name},</p>
        
        <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0 0 25px 0;">
            Your Rocket Tradeline account has been created by your broker. To complete your account setup and start purchasing tradelines, we need your digital signature.
        </p>
        
        <div style="background-color: #f0f9ff; border-left: 4px solid #17B26A; padding: 20px; border-radius: 6px; margin: 25px 0;">
            <h4 style="color: #374151; margin: 0 0 15px 0;">What you need to do:</h4>
            <ul style="margin: 0; padding-left: 20px; color: #6b7280; line-height: 1.6;">
                <li style="margin: 8px 0;">Click the "Complete Setup" button below</li>
                <li style="margin: 8px 0;">Upload your digital signature</li>
                <li style="margin: 8px 0;">Start purchasing tradelines immediately</li>
            </ul>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{signature_link}" 
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
        
        <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 25px 0 0 0;">
            If the button above doesn't work, you can copy and paste this link into your browser:
        </p>
        
        <div style="background-color: #f3f4f6; padding: 15px; border-radius: 6px; margin: 15px 0; word-break: break-all;">
            <p style="margin: 0; color: #374151; font-family: monospace; font-size: 14px;">
                {signature_link}
            </p>
        </div>
        
        <div style="background-color: #fef3c7; border: 1px solid #fbbf24; padding: 15px; border-radius: 6px; margin: 25px 0;">
            <p style="margin: 0; color: #92400e; font-weight: 600; font-size: 14px;">
                ⏰ Important: Complete your signature within 24 hours to activate your account.
            </p>
        </div>
        
        <p style="color: #6b7280; margin: 25px 0 0 0; font-size: 16px;">
            If you need assistance, please contact your broker or our support team at info@rockettradeline.com
        </p>
        {email_footer}"""
        
        # Prepare template parameters
        template_params = {
            "full_name": full_name,
            "signature_link": signature_link,
            "support_email": "info@rockettradeline.com"
        }
        
        # Send email using template
        from rockettradeline.rockettradeline.doctype.email_template_custom.email_template_custom import send_email_template
        
        send_email_template(
            template_name="Account Setup Required",
            recipients=[client_email],
            parameters=template_params
        )
        
        # Log the signature request
        frappe.logger().info(f"Signature request email sent to {client_email}")
        
    except Exception as e:
        frappe.log_error(f"Client signature email failed for {client_email}: {str(e)}", "Signature Email Error")
        raise e


@frappe.whitelist(allow_guest=True)
def validate_signature_key(key):
    """
    Validate client signature key
    
    Args:
        key (str): Signature key
        
    Returns:
        dict: Validation result with user email if valid
    """
    try:
        if not key:
            return {
                "success": False,
                "message": "Signature key is required"
            }
        
        # Find user with this signature key (using reset_password_key field)
        user_data = frappe.db.get_value(
            "User",
            {"reset_password_key": key, "enabled": 1},
            ["email", "last_reset_password_key_generated_on", "full_name"],
            as_dict=True
        )
        
        if not user_data:
            return {
                "success": False,
                "message": "Invalid or expired signature key"
            }
        
        # Check if key has expired (24 hours)
        if user_data.last_reset_password_key_generated_on:
            key_generated_time = user_data.last_reset_password_key_generated_on
            expiry_time = key_generated_time + timedelta(hours=24)
            
            if now_datetime() > expiry_time:
                return {
                    "success": False,
                    "message": "Signature key has expired. Please contact your broker for a new one."
                }
        
        # Check if signature is already completed
        customer_data = frappe.db.get_value(
            "Customer",
            {"email_id": user_data.email},
            ["has_signed_agreement", "name"],
            as_dict=True
        )
        
        if customer_data and customer_data.has_signed_agreement:
            return {
                "success": False,
                "message": "Signature has already been completed for this account."
            }
        
        return {
            "success": True,
            "message": "Signature key is valid",
            "email": user_data.email,
            "full_name": user_data.full_name,
            "customer_id": customer_data.name if customer_data else None
        }
        
    except Exception as e:
        frappe.log_error(f"Signature key validation failed: {str(e)}", "Signature Key Validation Error")
        return {
            "success": False,
            "message": "An error occurred while validating the signature key"
        }


@frappe.whitelist(allow_guest=True)
def upload_client_signature(key, file_content=None, filename=None):
    """
    Upload client signature using signature key
    
    Args:
        key (str): Signature key
        file_content (str): Base64 encoded file content or None for form upload
        filename (str): Original filename or None for form upload
        
    Returns:
        dict: Success/failure response
    """
    try:
        if not key:
            return {
                "success": False,
                "message": "Signature key is required"
            }
        
        # Validate the signature key first
        validation_result = validate_signature_key(key)
        if not validation_result.get("success"):
            return validation_result
        
        email = validation_result.get("email")
        customer_id = validation_result.get("customer_id")
        
        # Note: Customer record is optional - signature is saved against User
        
        # Handle file upload
        uploaded_file = None
        content = None
        fname = None
        
        # Check for form upload first
        files = frappe.request.files
        if files and 'file' in files:
            uploaded_file = files['file']
            if uploaded_file.filename and uploaded_file.filename != '':
                fname = secure_filename(uploaded_file.filename)
                content = uploaded_file.read()
        
        # Check for base64 upload
        elif file_content and filename:
            try:
                # Handle data URL format (e.g., "data:image/png;base64,iVBORw0KGgo...")
                if file_content.startswith('data:'):
                    file_content = file_content.split(',')[1]
                
                content = base64.b64decode(file_content)
                fname = secure_filename(filename)
            except Exception as e:
                return {
                    "success": False,
                    "message": f"Invalid file content: {str(e)}"
                }
        
        if not content or not fname:
            return {
                "success": False,
                "message": "No file provided. Use 'file' in form data or 'file_content' + 'filename' parameters"
            }
        
        # Validate file size (max 5MB)
        if len(content) > 5 * 1024 * 1024:
            return {
                "success": False,
                "message": "File size too large. Maximum size is 5MB"
            }
        
        # Validate file type (images and PDFs only)
        allowed_extensions = ['.png', '.jpg', '.jpeg', '.pdf', '.gif']
        file_ext = os.path.splitext(fname)[1].lower()
        if file_ext not in allowed_extensions:
            return {
                "success": False,
                "message": f"File type {file_ext} not allowed. Allowed types: {', '.join(allowed_extensions)}"
            }
        
        # Generate filename for signature
        signature_filename = f"client_signature_{email.replace('@', '_').replace('.', '_')}_{frappe.generate_hash(length=8)}{file_ext}"
        
        # Create or get folder for client_signature
        from .files import create_or_get_folder
        signature_folder = create_or_get_folder("client_signature", "Home")
        frappe.logger().info(f"Using folder '{signature_folder}' for client signature upload")
        
        # Save file using Frappe's file manager - attach to User instead of Customer
        file_doc = save_file(
            fname=signature_filename,
            content=content,
            dt="User",
            dn=email,
            folder=signature_folder,
            is_private=1  # Keep signatures private
        )
        
        # Update customer record (if exists)
        if customer_id:
            customer_doc = frappe.get_doc("Customer", customer_id)
            customer_doc.has_signed_agreement = 1
            # customer_doc.signature_date = now_datetime()
            
            # # Add a note about the signature
            # signature_note = f"\n[{now_datetime().strftime('%Y-%m-%d %H:%M:%S')}] Digital signature uploaded via broker registration"
            # existing_notes = customer_doc.notes or ""
            # customer_doc.notes = existing_notes + signature_note
            
            customer_doc.save(ignore_permissions=True)
        
        # Clear the signature key to prevent reuse
        user_doc = frappe.get_doc("User", email)
        user_doc.reset_password_key = None
        user_doc.last_reset_password_key_generated_on = None
        user_doc.save(ignore_permissions=True)
        
        frappe.db.commit()
        
        # Log successful signature upload
        frappe.logger().info(f"Client signature uploaded successfully for {email}")
        
        return {
            "success": True,
            "message": "Signature uploaded successfully! Your account setup is now complete.",
            "file": {
                "name": file_doc.name,
                "file_name": file_doc.file_name,
                "file_url": file_doc.file_url,
                "file_size": file_doc.file_size,
                "attached_to": "User",
                "attached_to_name": email
            },
            "user": {
                "email": email,
                "signature_uploaded": True,
                "signature_date": now_datetime()
            },
            "customer": {
                "id": customer_id,
                "has_signed_agreement": True if customer_id else None,
                "signature_date": now_datetime() if customer_id else None
            } if customer_id else None
        }
        
    except Exception as e:
        frappe.log_error(f"Client signature upload failed: {str(e)}", "Signature Upload Error")
        return {
            "success": False,
            "message": f"An error occurred while uploading your signature: {str(e)}"
        }

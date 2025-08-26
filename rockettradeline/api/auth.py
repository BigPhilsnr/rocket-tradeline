def get_authenticated_user():
    """
    Returns the authenticated user set by jwt_required, or None if not authenticated.
    """
    user = frappe.session.user if hasattr(frappe.session, 'user') and frappe.session.user != "Guest" else None
    return user
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
                        "message": "Authentication failed"
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
    """Send email verification email using Frappe's email system"""
    try:
        # Create verification link
        site_url = frappe.utils.get_url()
        verification_link = f"{site_url}/api/method/rockettradeline.api.auth.verify_email?token={verification_token}"
        
        # Check if Email Verification template exists
        if not frappe.db.exists('Email Template', 'Email Verification'):
            frappe.log_error(f"Email Template 'Email Verification' not found", "Email Template Missing")
            return False
            
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
            
        # Send email using Frappe's email queue (queue regardless of password config)
        try:
            # Create the email content with Rocket Tradeline branding
            site_url = frappe.utils.get_url()
            site_logo = f"{site_url}/assets/rockettradeline/logo.png"
            
            email_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f5f5f5;">
                <div style="background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <!-- Header with Logo -->
                    <div style="padding: 30px 30px 20px 30px; text-align: center;">
                        <div style="margin-bottom: 20px;">
                            <img src="{site_logo}" alt="Rocket Tradeline" style="max-height: 60px; max-width: 200px;" />
                        </div>
                    </div>
                    
                    <!-- Main Content -->
                    <div style="padding: 0 30px 30px 30px;">
                        <div style="margin-bottom: 25px;">
                            <p style="color: #374151; font-size: 16px; margin: 0 0 10px 0;">Hi {full_name},</p>
                            <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0;">
                                You just signed up for an account at Rocket Tradelines. To complete your registration and buy tradelines, click the button below.
                            </p>
                        </div>
                        
                        <!-- Verify Button -->
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{verification_link}" style="background-color: #17B26A; color: white; padding: 12px 24px; text-decoration: none; 
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
                    </div>
                    
                    <!-- Footer with Logo and Social Links -->
                    <div style="background-color: #f9fafb; padding: 30px; text-align: center; border-top: 1px solid #e5e7eb;">
                        <!-- Bottom Logo -->
                        <div style="margin-bottom: 20px;">
                            <img src="{site_logo}" alt="Rocket Tradeline" style="max-height: 40px; max-width: 150px;" />
                        </div>
                        
                        <!-- Social Media Icons -->
                        <div style="margin-bottom: 20px;">
                            <a href="#" style="display: inline-block; margin: 0 10px; text-decoration: none;">
                                <div style="width: 32px; height: 32px; background-color: #9ca3af; border-radius: 4px; display: inline-block;"></div>
                            </a>
                            <a href="#" style="display: inline-block; margin: 0 10px; text-decoration: none;">
                                <div style="width: 32px; height: 32px; background-color: #9ca3af; border-radius: 4px; display: inline-block;"></div>
                            </a>
                            <a href="#" style="display: inline-block; margin: 0 10px; text-decoration: none;">
                                <div style="width: 32px; height: 32px; background-color: #9ca3af; border-radius: 4px; display: inline-block;"></div>
                            </a>
                        </div>
                        
                        <!-- Footer Text -->
                        <div style="font-size: 12px; color: #9ca3af;">
                            <p style="margin: 0 0 10px 0;">
                                This email was sent to {user_email}. If you'd rather not receive this kind of email, you can 
                                <a href="#" style="color: #17B26A; text-decoration: none;">unsubscribe</a> or 
                                <a href="#" style="color: #17B26A; text-decoration: none;">manage your email preferences</a>.
                            </p>
                            <p style="margin: 0;">© 2025 Rocket Tradelines. All rights reserved</p>
                        </div>
                    </div>
                </div>
            </div>
            """
            
            frappe.sendmail(
                recipients=[user_email],
                subject=f"Verify Your Email Address - {frappe.local.site}",
                message=email_content,
                delayed=False,
                retry=3
            )
            
            # Return True if email was successfully queued
            return True
            
        except Exception as e:
            frappe.log_error(f"Email queue failed for {user_email}", "Email Queue Error") 
            return False
        
    except Exception as e:
        frappe.log_error(f"Email send failed for {user_email}", "Email Sending Error")
        return False

def is_email_verified(email):
    """Check if user email is verified"""
    try:
        user = frappe.get_doc("User", email)
        return getattr(user, 'email_verified', False)
    except:
        return False

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
def sign_up(email, full_name, password=None, phone=None):
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
        
        # Create user (initially unverified)
        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "full_name": full_name,
            "first_name": full_name.split()[0] if full_name else email,
            "last_name": full_name.split()[1] if full_name and len(full_name.split()) > 1 else None,
            "enabled": 1,
            "user_type": "Website User",
            "roles": [{"role": "Customer"}],
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
            "is_primary_contact": 1
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
            
            # Remove system fields that aren't needed in API response
            system_fields = ['docstatus', 'idx', 'owner', 'modified_by', 'creation', 'modified']
            for field in system_fields:
                customer.pop(field, None)
        
        # Get user files/attachments
        user_files = frappe.get_all("File",
            filters={
                "owner": user.name
            },
            fields=[
                "name", "file_name", "file_url", "file_size", "file_type",
                "is_private", "folder", "attached_to_doctype", "attached_to_name",
                "creation", "modified", "content_hash"
            ],
            order_by="creation desc"
        )
        
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
                "birth_date": user.birth_date,
                "phone": user.phone,
                "roles": [role.role for role in user.roles],
                "role_profile_name": role_profile_name,
                # "role_profile": role_profile_data,
                "user_type": user.user_type,
                "enabled": user.enabled
            },
            # "files": user_files
        }
        
        if customer:
            response_data["customer"] = customer
        
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
def update_profile(full_name=None, phone=None, user_image=None, gender=None, date_of_birth=None, 
                  social_security_number=None, address_line1=None, address_line2=None, city=None, 
                  state=None, zipcode=None, country=None, address_type="Personal"):
    """
    Update user profile, customer record, and address
    Uses standard Frappe authentication (session-based)
    """
    try:
        # Frappe automatically handles authentication with @frappe.whitelist()
        # frappe.session.user will be set to the authenticated user
        user_name = get_authenticated_user()
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
                "questionnaire_filled_date": getattr(customer, 'questionnaire_filled_date', None)
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
def update_customer_flags(is_seller=None, has_signed_agreement=None, is_questionnaire_filled=None):
    """
    Update customer flags (is_seller, has_signed_agreement, is_questionnaire_filled)
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
        
        # Track what was updated
        updated_fields = []
        
        # Update flags if provided
        if is_seller is not None:
            customer.is_seller = int(is_seller)
            updated_fields.append("is_seller")
        
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
            filters={"user": user_email},
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
                    <img src="{frappe.utils.get_url()}/assets/rockettradeline/images/logo.png" alt="Rocket Tradeline" style="max-height: 60px; max-width: 200px;" />
                </div>
                <div style="width: 60px; height: 60px; background-color: #ef4444; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 20px;">
                    <span style="color: white; font-size: 30px; font-weight: bold;">✗</span>
                </div>
                <h1 style="color: #1f2937; font-size: 24px; margin-bottom: 15px;">Invalid Verification Link</h1>
                <p style="color: #6b7280; font-size: 16px; line-height: 1.6; margin-bottom: 30px;">
                    The verification link appears to be incomplete or corrupted. Please check your email for the correct verification link.
                </p>
                <a href="https://staging.rockettradeline.com" style="background-color: #17B26A; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">Go to Homepage</a>
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
                    <img src="{frappe.utils.get_url()}/assets/rockettradeline/images/logo.png" alt="Rocket Tradeline" style="max-height: 60px; max-width: 200px;" />
                </div>
                <div style="width: 60px; height: 60px; background-color: #ef4444; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 20px;">
                    <span style="color: white; font-size: 30px; font-weight: bold;">✗</span>
                </div>
                <h1 style="color: #1f2937; font-size: 24px; margin-bottom: 15px;">Invalid Verification Token</h1>
                <p style="color: #6b7280; font-size: 16px; line-height: 1.6; margin-bottom: 30px;">
                    The verification link you clicked is invalid or has already been used. Please check your email for the correct link or request a new verification email.
                </p>
                <a href="https://staging.rockettradeline.com" style="background-color: #17B26A; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">Go to Homepage</a>
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
                    <a href="https://staging.rockettradeline.com" style="background-color: #17B26A; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">Go to Homepage</a>
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
                <img src="{frappe.utils.get_url()}/assets/rockettradeline/images/logo.png" alt="Rocket Tradeline" style="max-height: 60px; max-width: 200px;" />
            </div>
            <div style="width: 60px; height: 60px; background-color: #17B26A; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 20px;">
                <span style="color: white; font-size: 30px; font-weight: bold;">✓</span>
            </div>
            <h1 style="color: #1f2937; font-size: 24px; margin-bottom: 15px;">Your Account Has Been Verified!</h1>
            <p style="color: #6b7280; font-size: 16px; line-height: 1.6; margin-bottom: 30px;">
                Congratulations! Your email address has been successfully verified. You can now access your Rocket Tradeline account and start buying tradelines.
            </p>
            <a href="https://staging.rockettradeline.com" style="background-color: #17B26A; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">Click Here to Login</a>
        </div>
        """
        
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
            <a href="https://staging.rockettradeline.com" style="background-color: #17B26A; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">Go to Homepage</a>
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

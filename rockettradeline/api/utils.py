import frappe
from frappe import _
from frappe.utils import validate_email_address, cint, flt
# auth helper is not needed here; use frappe.session.user set by jwt_required
import re

def validate_phone(phone):
    """
    Validate phone number format
    """
    if not phone:
        return True
    
    # Remove all non-digit characters
    phone_digits = re.sub(r'\D', '', phone)
    
    # Check if it's a valid length (assuming 10+ digits)
    if len(phone_digits) < 10:
        return False
    
    return True

def validate_tradeline_data(data):
    """
    Validate tradeline data
    """
    errors = []
    
    # Required fields
    required_fields = ['bank', 'age_year', 'credit_limit', 'price', 
                      'max_spots', 'closing_date', 'card_holder', 
                      'mailing_address']
    
    for field in required_fields:
        if not data.get(field):
            errors.append(f"{field} is required")
    
    # Validate numeric fields
    if data.get('age_year') and cint(data['age_year']) <= 0:
        errors.append("Age year must be positive")
    
    if data.get('credit_limit') and cint(data['credit_limit']) <= 0:
        errors.append("Credit limit must be positive")
    
    if data.get('price') and flt(data['price']) <= 0:
        errors.append("Price must be positive")
    
    if data.get('max_spots') and cint(data['max_spots']) <= 0:
        errors.append("Max spots must be positive")
    
    if data.get('closing_date'):
        closing_date = cint(data['closing_date'])
        if closing_date < 1 or closing_date > 31:
            errors.append("Closing date must be between 1 and 31")
    
    return errors

def get_user_permissions():
    """
    Get current user permissions
    """
    user = frappe.session.user

    if user == "Administrator":
        return {
            "is_admin": True,
            "can_manage_users": True,
            "can_manage_tradelines": True,
            "can_manage_website": True
        }

    roles = frappe.get_roles(user)

    return {
        "is_admin": "System Manager" in roles,
        "can_manage_users": "System Manager" in roles,
        "can_manage_tradelines": any(role in roles for role in ["System Manager", "Tradeline Manager"]),
        "can_manage_website": any(role in roles for role in ["System Manager", "Website Manager"])
    }

def format_currency(amount, currency="USD"):
    """
    Format currency amount
    """
    if not amount:
        return f"0.00 {currency}"
    
    return f"{flt(amount, 2):,.2f} {currency}"

def sanitize_search_term(term):
    """
    Sanitize search term to prevent SQL injection
    """
    if not term:
        return ""
    
    # Remove special characters except spaces, letters, and numbers
    sanitized = re.sub(r'[^\w\s-]', '', str(term))
    
    # Limit length
    return sanitized[:100]

def get_pagination_info(total_count, limit, start):
    """
    Get pagination information
    """
    limit = cint(limit) or 20
    start = cint(start) or 0
    
    has_next = (start + limit) < total_count
    has_prev = start > 0
    
    return {
        "total_count": total_count,
        "limit": limit,
        "start": start,
        "has_next": has_next,
        "has_prev": has_prev,
        "current_page": (start // limit) + 1,
        "total_pages": (total_count + limit - 1) // limit
    }

def log_api_call(endpoint, user, data=None, success=True, error=None):
    """
    Log API call for debugging and monitoring
    """
    try:
        # Create a simple log entry
        frappe.logger().info(f"API Call: {endpoint} | User: {user} | Success: {success} | Error: {error}")
        
        # You could also create a custom DocType for API logs if needed
        # frappe.get_doc({
        #     "doctype": "API Log",
        #     "endpoint": endpoint,
        #     "user": user,
        #     "data": str(data) if data else None,
        #     "success": success,
        #     "error": error
        # }).insert()
        
    except Exception:
        # Don't fail the API call if logging fails
        pass

def send_email_notification(to_email, subject, template, context=None):
    """
    Send email notification
    """
    try:
        if not context:
            context = {}
        
        frappe.sendmail(
            recipients=[to_email],
            subject=subject,
            template=template,
            args=context
        )
        
        return True
    except Exception as e:
        frappe.logger().error(f"Failed to send email: {str(e)}")
        return False

def generate_api_key(user_id):
    """
    Generate API key for user
    """
    try:
        user = frappe.get_doc("User", user_id)
        
        if not user.api_key:
            user.api_key = frappe.generate_hash(length=40)
            user.save(ignore_permissions=True)
        
        return user.api_key
    except Exception as e:
        frappe.logger().error(f"Failed to generate API key: {str(e)}")
        return None

def validate_api_key(api_key):
    """
    Validate API key and return user
    """
    try:
        user = frappe.get_all("User", 
            filters={"api_key": api_key, "enabled": 1},
            fields=["name", "email", "full_name"],
            limit=1
        )
        
        if user:
            return user[0]
        return None
    except Exception as e:
        frappe.logger().error(f"Failed to validate API key: {str(e)}")
        return None

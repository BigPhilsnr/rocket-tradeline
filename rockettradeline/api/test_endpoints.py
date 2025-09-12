import frappe
from .utils import get_authenticated_user, is_administrator
from .auth import jwt_required

@frappe.whitelist(allow_guest=True)
def simple_test():
    """
    Simple test endpoint without JWT to verify basic functionality
    """
    try:
        return {
            "success": True,
            "message": "Simple test endpoint works",
            "user": frappe.session.user,
            "timestamp": frappe.utils.now()
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist(allow_guest=True)
@jwt_required()
def test_jwt_decorator():
    """
    Test endpoint with JWT decorator
    """
    try:
        user = get_authenticated_user()
        return {
            "success": True,
            "message": "JWT decorator works",
            "user": user,
            "session_user": frappe.session.user,
            "is_admin": is_administrator(user) if user else False
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist(allow_guest=True)
def test_jwt_manual():
    """
    Test JWT validation manually without decorator
    """
    try:
        from .auth import validate_jwt_token
        
        # Get Authorization header
        auth_header = frappe.get_request_header("X-Authorization") or frappe.get_request_header("Authorization")
        
        if not auth_header:
            return {
                "success": False,
                "message": "No Authorization header found"
            }
        
        if not auth_header.startswith("Bearer "):
            return {
                "success": False,
                "message": "Invalid Authorization header format"
            }
        
        # Extract JWT token
        jwt_token = auth_header.replace("Bearer ", "")
        
        # Validate token
        payload = validate_jwt_token(jwt_token)
        
        if not payload:
            return {
                "success": False,
                "message": "Invalid JWT token"
            }
        
        return {
            "success": True,
            "message": "JWT token is valid",
            "payload": payload,
            "user": payload.get('user_id'),
            "is_admin": is_administrator(payload.get('user_id'))
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

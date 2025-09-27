import frappe
from .utils import  is_administrator
from .auth import jwt_required, get_authenticated_user

@frappe.whitelist(allow_guest=True)
@jwt_required()
def create_address(address_title, address_line1, address_line2=None, city=None, state=None, country=None, pincode=None, email=None, phone=None, zip_code=None, is_default=0, address_type="Personal"):
    """
    Create a new address
    """
    try:
        
        if zip_code:
            pincode = zip_code  # Support both pincode and zip_code
        # Get authenticated user
        user = get_authenticated_user()
        if not user:
            frappe.local.response.http_status_code = 401
            return {
                "success": False,
                "message": "Authentication required"
            }
        
        # Validate required fields
        if not address_title or not address_line1:
            return {
                "success": False,
                "message": "Address title and address line 1 are required"
            }
            
        # Get or create Customer for this user
        customer_name= frappe.db.get_value("Customer", {"email_id": user}, "name")
        
        # Create address document
        address_doc = frappe.get_doc({
            "doctype": "Address",
            "address_title": address_title,
            "address_line1": address_line1,
            "address_line2": address_line2,
            "city": city,
            "state": state,
            "country": country,
            "pincode": pincode,
            "email_id": email,
            "phone": phone,
            "address_type": address_type,
             "is_primary_address": is_default,
            "is_shipping_address": 0,
            "links": [{
                "link_doctype": "Customer",
                "link_name": customer_name
            }]
        })

        address_doc.insert(ignore_permissions=True)

        return {
            "success": True,
            "message": "Address created successfully",
            "address": {
                "name": address_doc.name,
                "address_title": address_doc.address_title,
                "address_line1": address_doc.address_line1,
                "address_line2": address_doc.address_line2,
                "city": address_doc.city,
                "state": address_doc.state,
                "country": address_doc.country,
                "zip_code": address_doc.pincode,
                "email_id": address_doc.email_id,
                "is_default": address_doc.is_primary_address,
                "phone": address_doc.phone,
                "address_type": address_doc.address_type
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
def update_address(address_id, address_title=None, address_line1=None, address_line2=None, city=None, state=None, country=None, pincode=None, email=None,zip_code=None, is_default=None  ):
    """
    Update an existing address
    """
    try:
        
        if zip_code:
            pincode = zip_code  # Support both pincode and zip_code
        # Get authenticated user
        user = get_authenticated_user()
        if not user:
            frappe.local.response.http_status_code = 401
            return {
                "success": False,
                "message": "Authentication required"
            }
        
        # Get address document
        address_doc = frappe.get_doc("Address", address_id)
        
        # Check if user can update this address (either admin or address belongs to user's email)
        if not is_administrator(user) and address_doc.email_id != user:
            return {
                "success": False,
                "message": "Access denied. You can only update your own addresses."
            }
        
        # Update fields if provided
        if address_title is not None:
            address_doc.address_title = address_title
        if address_line1 is not None:
            address_doc.address_line1 = address_line1
        if address_line2 is not None:
            address_doc.address_line2 = address_line2
        if city is not None:
            address_doc.city = city
        if state is not None:
            address_doc.state = state
        if country is not None:
            address_doc.country = country
        if pincode is not None:
            address_doc.pincode = pincode
        if email is not None:
            address_doc.email_id = email
        if is_default is not None:
            address_doc.is_primary_address = int(is_default)
        address_doc.save()
        
        return {
            "success": True,
            "message": "Address updated successfully",
            "address": {
                "name": address_doc.name,
                "address_title": address_doc.address_title,
                "address_line1": address_doc.address_line1,
                "address_line2": address_doc.address_line2,
                "city": address_doc.city,
                "state": address_doc.state,
                "country": address_doc.country,
                "zip_code": address_doc.pincode,
                "is_default": address_doc.is_primary_address,
                "email_id": address_doc.email_id
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
def get_addresses_by_email(email):
    """
    Get all addresses for a specific email
    """
    try:
        # Get authenticated user
        user = get_authenticated_user()
        if not user:
            frappe.local.response.http_status_code = 401
            return {
                "success": False,
                "message": "Authentication required"
            }
        
        # Check if user can access addresses for this email (either admin or requesting own addresses)
        if not is_administrator(user) and email != user:
            return {
                "success": False,
                "message": "Access denied. You can only view your own addresses."
            }
        
        # Get addresses for email
        addresses = frappe.get_all("Address", 
            filters={"email_id": email},
            fields=["name", "address_title", "address_line1", "address_line2", "city", "state", "country", "pincode", "email_id", "address_type", "phone", "is_primary_address"],
            order_by="creation desc"
        )
        
        # Map fields: pincode -> zip_code, is_primary_address -> is_default
        for address in addresses:
            address["zip_code"] = address.pop("pincode", None)
            address["is_default"] = address.pop("is_primary_address", 0)
        
        return {
            "success": True,
            "addresses": addresses
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_address(address_id):
    """
    Get a specific address by ID
    """
    try:
        # Get authenticated user
        user = get_authenticated_user()
        if not user:
            frappe.local.response.http_status_code = 401
            return {
                "success": False,
                "message": "Authentication required"
            }
        
        # Get address document
        address_doc = frappe.get_doc("Address", address_id)
        
        # Check if user can access this address (either admin or address belongs to user's email)
        if not is_administrator(user) and address_doc.email_id != user:
            return {
                "success": False,
                "message": "Access denied. You can only view your own addresses."
            }
        
        return {
            "success": True,
            "address": {
                "name": address_doc.name,
                "address_title": address_doc.address_title,
                "address_line1": address_doc.address_line1,
                "address_line2": address_doc.address_line2,
                "city": address_doc.city,
                "state": address_doc.state,
                "country": address_doc.country,
                "pincode": address_doc.pincode,
                "email_id": address_doc.email_id,
                "address_type": address_doc.address_type
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
def delete_address(address_id):
    """
    Delete an address
    """
    try:
        # Get authenticated user
        user = get_authenticated_user()
        if not user:
            frappe.local.response.http_status_code = 401
            return {
                "success": False,
                "message": "Authentication required"
            }
        
        # Get address document to check permissions
        address_doc = frappe.get_doc("Address", address_id)
        
        # Check if user can delete this address (either admin or address belongs to user's email)
        if not is_administrator(user) and address_doc.email_id != user:
            return {
                "success": False,
                "message": "Access denied. You can only delete your own addresses."
            }
        
        frappe.delete_doc("Address", address_id)
        
        return {
            "success": True,
            "message": "Address deleted successfully"
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "success": False,
            "message": str(e)
        }

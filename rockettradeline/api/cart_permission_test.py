import frappe
from frappe import _
import json
from datetime import datetime, timedelta

@frappe.whitelist(allow_guest=True)
def test_cart_permissions():
    """Test if DocType exists and basic operations work"""
    try:
        # Test 1: Check if DocType exists
        if not frappe.db.exists("DocType", "Tradeline Cart"):
            return {
                'success': False, 
                'error': 'Tradeline Cart DocType not found',
                'step': 'DocType Check'
            }
        
        # Test 2: Try to create cart with ignore_permissions
        cart_data = {
            'doctype': 'Tradeline Cart',
            'user_id': 'Administrator',
            'status': 'Draft',
            'subtotal': 0.0,
            'total_amount': 0.0,
            'cart_expiry': datetime.now() + timedelta(days=7)
        }
        
        # Check if Administrator cart already exists
        existing = frappe.db.get_value(
            'Tradeline Cart', 
            {'user_id': 'Administrator', 'status': ['in', ['Draft', 'Active']]},
            'name'
        )
        
        if existing:
            cart_name = existing
            message = "Found existing cart"
        else:
            cart = frappe.get_doc(cart_data)
            cart.insert(ignore_permissions=True)
            cart_name = cart.name
            message = "Created new cart"
        
        # Test 3: Try to read the cart
        cart = frappe.get_doc('Tradeline Cart', cart_name)
        
        return {
            'success': True,
            'cart_id': cart_name,
            'message': message,
            'cart_data': {
                'user_id': cart.user_id,
                'status': cart.status,
                'total_amount': cart.total_amount,
                'item_count': len(cart.items) if cart.items else 0
            }
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'step': 'Cart Operations'
        }

@frappe.whitelist(allow_guest=True)
def test_add_cart_item(cart_id):
    """Test adding an item to cart"""
    try:
        # Get the cart
        cart = frappe.get_doc('Tradeline Cart', cart_id)
        
        # Find an existing tradeline or create one without bank dependency
        existing_tradeline = frappe.db.get_value('Tradeline', {'status': 'Active'}, ['name', 'price'])
        
        if existing_tradeline:
            test_tradeline_id = existing_tradeline[0]
            price = existing_tradeline[1]
        else:
            # Create a minimal test tradeline
            test_tradeline_id = "TL-TEST-001"
            tradeline = frappe.get_doc({
                'doctype': 'Tradeline',
                'name': test_tradeline_id,
                'price': 150.0,
                'credit_limit': 5000,
                'status': 'Active'
            })
            # Set only required fields
            tradeline.insert(ignore_permissions=True)
            price = 150.0
        
        # Add item to cart
        cart.append('items', {
            'tradeline': test_tradeline_id,
            'quantity': 1,
            'rate': price,
            'amount': price
        })
        
        cart.save(ignore_permissions=True)
        
        return {
            'success': True,
            'message': 'Item added to cart',
            'cart_total': cart.total_amount,
            'item_count': len(cart.items)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

# Using frappe.session.user set by jwt_required decorator
import frappe
from frappe import _
import json
from datetime import datetime, timedelta

@frappe.whitelist(allow_guest=True)
def create_cart():
    """Create a new shopping cart for the current user - simple version"""
    try:
        # Get current user from token in the request
        auth_header = frappe.get_request_header("Authorization")
        if not auth_header:
            return {'success': False, 'error': 'Authorization required'}
            
        # Check if user already has an active cart
        user = frappe.session.user
        if not user:
            return {'success': False, 'error': 'Authentication required'}
        
        existing_cart = frappe.db.get_value(
            'Tradeline Cart',
            {'user_id': user, 'status': 'Active'},
            'name'
        )
        
        if existing_cart:
            return {
                'success': True,
                'cart_id': existing_cart,
                'message': 'Active cart found'
            }
        
        # Create new cart
        cart = frappe.get_doc({
            'doctype': 'Tradeline Cart',
            'user_id': frappe.session.user,
            'status': 'Active',
            'subtotal': 0.0,
            'total_amount': 0.0,
            'cart_expiry': datetime.now() + timedelta(days=7)
        })
        cart.insert()
        
        return {
            'success': True,
            'cart_id': cart.name,
            'message': 'Cart created successfully'
        }
        
    except Exception as e:
        frappe.log_error(f"Cart creation error: {str(e)}")
        return {'success': False, 'error': str(e)}

@frappe.whitelist(allow_guest=True)
def get_cart(cart_id=None):
    """Get cart details"""
    try:
        user = frappe.session.user
        if not user:
            return {'success': False, 'error': 'Authentication required'}
        
        if not cart_id:
            # Get user's active cart
            cart_id = frappe.db.get_value(
                'Tradeline Cart',
                {'user_id': user, 'status': 'Active'},
                'name'
            )
            
        if not cart_id:
            return {'success': False, 'error': 'No active cart found'}
            
        cart = frappe.get_doc('Tradeline Cart', cart_id)
        
        # Verify ownership
        if cart.user_id != user:
            return {'success': False, 'error': 'Access denied'}
        
        return {
            'success': True,
            'cart': {
                'cart_id': cart.name,
                'status': cart.status,
                'subtotal': cart.subtotal,
                'total_amount': cart.total_amount,
                'items': [
                    {
                        'tradeline_id': item.tradeline,
                        'quantity': item.quantity,
                        'rate': item.rate,
                        'amount': item.amount
                    } for item in cart.items
                ]
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Get cart error: {str(e)}")
        return {'success': False, 'error': str(e)}

@frappe.whitelist(allow_guest=True)
def add_to_cart():
    """Add item to cart"""
    try:
        user = frappe.session.user
        if not user:
            return {'success': False, 'error': 'Authentication required'}
        
        data = json.loads(frappe.request.data)
        cart_id = data.get('cart_id')
        tradeline_id = data.get('tradeline_id')
        quantity = int(data.get('quantity', 1))
        
        if not cart_id or not tradeline_id:
            return {'success': False, 'error': 'Cart ID and Tradeline ID required'}
        
        cart = frappe.get_doc('Tradeline Cart', cart_id)
        
        # Verify ownership
        if cart.user_id != user:
            return {'success': False, 'error': 'Access denied'}
        
        # Get tradeline details
        tradeline = frappe.get_doc('Tradeline', tradeline_id)
        
        # Check if item already exists in cart
        existing_item = None
        for item in cart.items:
            if item.tradeline == tradeline_id:
                existing_item = item
                break
        
        if existing_item:
            # Update quantity
            existing_item.quantity += quantity
            existing_item.amount = existing_item.quantity * existing_item.rate
        else:
            # Add new item
            cart.append('items', {
                'tradeline': tradeline_id,
                'quantity': quantity,
                'rate': tradeline.price,
                'amount': quantity * tradeline.price
            })
        
        cart.save()
        
        return {
            'success': True,
            'message': 'Item added to cart successfully',
            'cart_total': cart.total_amount
        }
        
    except Exception as e:
        frappe.log_error(f"Add to cart error: {str(e)}")
        return {'success': False, 'error': str(e)}

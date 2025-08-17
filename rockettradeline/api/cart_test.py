import frappe
from frappe import _
import json
from datetime import datetime, timedelta

@frappe.whitelist(allow_guest=True)
def test_create_cart():
    """Test cart creation - bypasses auth for testing"""
    try:
        # For testing, use Administrator user
        test_user = "Administrator"
        
        # Check if user already has an active cart
        existing_cart = frappe.db.get_value(
            'Tradeline Cart',
            {'user_id': test_user, 'status': 'Active'},
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
            'user_id': test_user,
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
        frappe.log_error(f"Test cart creation error: {str(e)}")
        return {'success': False, 'error': str(e)}

@frappe.whitelist(allow_guest=True)
def test_add_to_cart(cart_id, tradeline_id="TL-TEST", quantity=1):
    """Test adding item to cart"""
    try:
        cart = frappe.get_doc('Tradeline Cart', cart_id)
        
        # Create a test tradeline if it doesn't exist
        if not frappe.db.exists('Tradeline', tradeline_id):
            test_tradeline = frappe.get_doc({
                'doctype': 'Tradeline',
                'name': tradeline_id,
                'bank': 'Test Bank',
                'price': 100.0,
                'credit_limit': 5000,
                'status': 'Active'
            })
            test_tradeline.insert()
            price = 100.0
        else:
            tradeline = frappe.get_doc('Tradeline', tradeline_id)
            price = tradeline.price
        
        # Add item to cart
        cart.append('items', {
            'tradeline': tradeline_id,
            'quantity': int(quantity),
            'rate': price,
            'amount': int(quantity) * price
        })
        
        cart.save()
        
        return {
            'success': True,
            'message': 'Item added to cart successfully',
            'cart_total': cart.total_amount
        }
        
    except Exception as e:
        frappe.log_error(f"Test add to cart error: {str(e)}")
        return {'success': False, 'error': str(e)}

@frappe.whitelist(allow_guest=True)
def test_get_cart(cart_id):
    """Test getting cart details"""
    try:
        cart = frappe.get_doc('Tradeline Cart', cart_id)
        
        return {
            'success': True,
            'cart': {
                'cart_id': cart.name,
                'user_id': cart.user_id,
                'status': cart.status,
                'subtotal': cart.subtotal,
                'total_amount': cart.total_amount,
                'item_count': len(cart.items),
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
        frappe.log_error(f"Test get cart error: {str(e)}")
        return {'success': False, 'error': str(e)}

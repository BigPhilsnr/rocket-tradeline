from rockettradeline.api.auth import jwt_required, get_current_user, get_authenticated_user
# Copyright (c) 2025, RocketTradeline and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt, now, add_days, now_datetime, get_datetime
import json
from rockettradeline.api.auth import jwt_required, get_current_user, get_authenticated_user

def is_administrator(user):
    """Check if user has Administrator role or profile"""
    if user == "Administrator":
        return True
    
    # Check if user has Administrator role profile
    user_roles = frappe.get_roles(user)
    return "System Manager" in user_roles

def verify_cart_access(cart, current_user):
    """Verify if user has access to cart (owner or administrator)"""
    return cart.user_id == current_user or is_administrator(current_user)

@frappe.whitelist(allow_guest=True)
@jwt_required()
def create_cart():
    """Create a new shopping cart for the current user"""
    try:
        current_user = get_authenticated_user()
        if not current_user:
            return {'success': False, 'error': 'Authentication required'}
        
        # Check if user already has an active cart
        existing_cart = frappe.db.get_value(
            'Tradeline Cart',
            {'user_id': current_user, 'status': 'Active'},
            'name'
        )
        
        if existing_cart:
            cart = frappe.get_doc('Tradeline Cart', existing_cart)
            return {
                'success': True,
                'message': 'Active cart found',
                'cart': cart.as_dict(),
                'cart_id': cart.name
            }
        
        # Get customer for user
        customer = frappe.db.get_value('Customer', {'email_id': current_user}, 'name')
        
        # Create new cart
        cart = frappe.get_doc({
            'doctype': 'Tradeline Cart',
            'user_id': current_user,
            'customer': customer,
            'status': 'Active',
            'cart_expiry': add_days(now(), 30)
        })
        cart.insert()
        
        return {
            'success': True,
            'message': 'Cart created successfully',
            'cart': cart.as_dict(),
            'cart_id': cart.name
        }
        
    except Exception as e:
        frappe.log_error(f"Cart creation error: {str(e)}", "Cart API Error")
        return {'success': False, 'error': str(e)}

@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_cart(cart_id=None):
    """Get user's cart (active cart if no cart_id provided)"""
    try:
        current_user = get_authenticated_user()
        if not current_user:
            return {'success': False, 'error': 'Authentication required'}
        
        if cart_id:
            # Get specific cart
            cart = frappe.get_doc('Tradeline Cart', cart_id)
            # Verify ownership or admin access
            if not verify_cart_access(cart, current_user):
                return {'success': False, 'error': 'Access denied'}
        else:
            # Get active cart
            cart_name = frappe.db.get_value(
                'Tradeline Cart',
                {'user_id': current_user, 'status': 'Active'},
                'name'
            )
            
            if not cart_name:
                return {'success': False, 'error': 'No active cart found', 'user': current_user}
            
            cart = frappe.get_doc('Tradeline Cart', cart_name)
        
        # Get detailed cart info with items
        cart_data = cart.as_dict()
        
        # Add item details
        for item in cart_data.get('items', []):
            if item.get('tradeline'):
                tradeline = frappe.get_doc('Tradeline', item['tradeline'])
                item['tradeline_details'] = {
                    'bank': tradeline.bank,
                    'age_year': tradeline.age_year,
                    'age_month': tradeline.age_month,
                    'credit_limit': tradeline.credit_limit,
                    'max_spots': tradeline.max_spots,
                    'status': tradeline.status
                }
        
        return {
            'success': True,
            'cart': cart_data,
            'cart_summary': {
                'cart_id': cart.name,
                'item_count': len(cart.items),
                'subtotal': cart.subtotal,
                'discount_amount': cart.discount_amount,
                'tax_amount': cart.tax_amount,
                'total_amount': cart.total_amount,
                'is_expired': cart.is_expired()
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Get cart error: {str(e)}", "Cart API Error")
        return {'success': False, 'error': str(e)}

@frappe.whitelist(allow_guest=True)
@jwt_required()
def add_to_cart(tradeline_id, quantity=1, cart_id=None):
    """Add item to cart or update quantity if exists"""
    try:
        current_user = get_authenticated_user()
        if not current_user:
            return {'success': False, 'error': 'Authentication required'}
        
        quantity = cint(quantity)
        if quantity <= 0:
            return {'success': False, 'error': 'Quantity must be greater than 0'}
        
        # Validate tradeline exists and is active
        tradeline = frappe.get_doc('Tradeline', tradeline_id)
        if tradeline.status != 'Active':
            return {'success': False, 'error': 'Tradeline is not active'}
        
        if quantity > tradeline.max_spots:
            return {'success': False, 'error': f'Only {tradeline.max_spots} spots available'}
        
        # Get or create cart
        if cart_id:
            cart = frappe.get_doc('Tradeline Cart', cart_id)
            if not verify_cart_access(cart, current_user):
                return {'success': False, 'error': 'Access denied'}
        else:
            # Get active cart or create new one
            cart_name = frappe.db.get_value(
                'Tradeline Cart',
                {'user_id': current_user, 'status': 'Active'},
                'name'
            )
            
            if cart_name:
                cart = frappe.get_doc('Tradeline Cart', cart_name)
            else:
                # Create new cart
                customer = frappe.db.get_value('Customer', {'email_id': current_user}, 'name')
                cart = frappe.get_doc({
                    'doctype': 'Tradeline Cart',
                    'user_id': current_user,
                    'customer': customer,
                    'status': 'Active',
                    'cart_expiry': add_days(now(), 30)
                })
                cart.insert()
        
        # Check if item already exists in cart
        existing_item = None
        for item in cart.items:
            if item.tradeline == tradeline_id:
                existing_item = item
                break
        
        if existing_item:
            # Update quantity
            new_quantity = existing_item.quantity + quantity
            if new_quantity > tradeline.max_spots:
                return {'success': False, 'error': f'Total quantity would exceed available spots ({tradeline.max_spots})'}
            
            existing_item.quantity = new_quantity
            existing_item.amount = existing_item.quantity * existing_item.rate
        else:
            # Add new item
            cart.append('items', {
                'tradeline': tradeline_id,
                'tradeline_name': tradeline.bank,
                'quantity': quantity,
                'rate': tradeline.price,
                'amount': tradeline.price * quantity
            })
        
        cart.save()
        
        return {
            'success': True,
            'message': 'Item added to cart successfully',
            'cart': cart.as_dict(),
            'cart_summary': {
                'cart_id': cart.name,
                'item_count': len(cart.items),
                'total_amount': cart.total_amount
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Add to cart error: {str(e)}", "Cart API Error")
        return {'success': False, 'error': str(e)}

@frappe.whitelist(allow_guest=True)
@jwt_required()
def remove_from_cart(tradeline_id, cart_id=None):
    """Remove item from cart"""
    try:
        current_user = get_authenticated_user()
        if not current_user:
            return {'success': False, 'error': 'Authentication required'}
        
        # Get cart
        if cart_id:
            cart = frappe.get_doc('Tradeline Cart', cart_id)
            if not verify_cart_access(cart, current_user):
                return {'success': False, 'error': 'Access denied'}
        else:
            cart_name = frappe.db.get_value(
                'Tradeline Cart',
                {'user_id': current_user, 'status': 'Active'},
                'name'
            )
            if not cart_name:
                return {'success': False, 'error': 'No active cart found'}
            cart = frappe.get_doc('Tradeline Cart', cart_name)
        
        # Remove item
        item_found = False
        for i, item in enumerate(cart.items):
            if item.tradeline == tradeline_id:
                del cart.items[i]
                item_found = True
                break
        
        if not item_found:
            return {'success': False, 'error': 'Item not found in cart'}
        
        cart.save()
        
        return {
            'success': True,
            'message': 'Item removed from cart successfully',
            'cart': cart.as_dict(),
            'cart_summary': {
                'cart_id': cart.name,
                'item_count': len(cart.items),
                'total_amount': cart.total_amount
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Remove from cart error: {str(e)}", "Cart API Error")
        return {'success': False, 'error': str(e)}

@frappe.whitelist(allow_guest=True)
@jwt_required()
def update_cart_item(tradeline_id, quantity, cart_id=None):
    """Update item quantity in cart"""
    try:
        current_user = get_authenticated_user()
        if not current_user:
            return {'success': False, 'error': 'Authentication required'}
        
        quantity = cint(quantity)
        
        # If quantity is 0 or negative, remove the item
        if quantity <= 0:
            return remove_from_cart(tradeline_id, cart_id)
        
        # Get cart
        if cart_id:
            cart = frappe.get_doc('Tradeline Cart', cart_id)
            if not verify_cart_access(cart, current_user):
                return {'success': False, 'error': 'Access denied'}
        else:
            cart_name = frappe.db.get_value(
                'Tradeline Cart',
                {'user_id': current_user, 'status': 'Active'},
                'name'
            )
            if not cart_name:
                return {'success': False, 'error': 'No active cart found'}
            cart = frappe.get_doc('Tradeline Cart', cart_name)
        
        # Validate tradeline availability
        tradeline = frappe.get_doc('Tradeline', tradeline_id)
        if quantity > tradeline.max_spots:
            return {'success': False, 'error': f'Only {tradeline.max_spots} spots available'}
        
        # Update item
        item_found = False
        for item in cart.items:
            if item.tradeline == tradeline_id:
                item.quantity = quantity
                item.amount = item.quantity * item.rate
                item_found = True
                break
        
        if not item_found:
            return {'success': False, 'error': 'Item not found in cart'}
        
        cart.save()
        
        return {
            'success': True,
            'message': 'Cart item updated successfully',
            'cart': cart.as_dict(),
            'cart_summary': {
                'cart_id': cart.name,
                'item_count': len(cart.items),
                'total_amount': cart.total_amount
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Update cart item error: {str(e)}", "Cart API Error")
        return {'success': False, 'error': str(e)}

@frappe.whitelist(allow_guest=True)
@jwt_required()
def clear_cart(cart_id=None):
    """Clear all items from cart"""
    try:
        current_user = get_authenticated_user()
        if not current_user:
            return {'success': False, 'error': 'Authentication required'}
        
        # Get cart
        if cart_id:
            cart = frappe.get_doc('Tradeline Cart', cart_id)
            if not verify_cart_access(cart, current_user):
                return {'success': False, 'error': 'Access denied'}
        else:
            cart_name = frappe.db.get_value(
                'Tradeline Cart',
                {'user_id': current_user, 'status': 'Active'},
                'name'
            )
            if not cart_name:
                return {'success': False, 'error': 'No active cart found'}
            cart = frappe.get_doc('Tradeline Cart', cart_name)
        
        # Clear items
        cart.items = []
        cart.save()
        
        return {
            'success': True,
            'message': 'Cart cleared successfully',
            'cart': cart.as_dict()
        }
        
    except Exception as e:
        frappe.log_error(f"Clear cart error: {str(e)}", "Cart API Error")
        return {'success': False, 'error': str(e)}

@frappe.whitelist(allow_guest=True)
@jwt_required()
def update_payment_mode(payment_mode, cart_id=None):
    """Update cart payment mode"""
    try:
        current_user = get_authenticated_user()
        if not current_user:
            return {'success': False, 'error': 'Authentication required'}
        
        # Validate payment mode
        if not frappe.db.exists('Mode of Payment', payment_mode):
            return {'success': False, 'error': 'Invalid payment mode'}
        
        # Get cart
        if cart_id:
            cart = frappe.get_doc('Tradeline Cart', cart_id)
            if not verify_cart_access(cart, current_user):
                return {'success': False, 'error': 'Access denied'}
        else:
            cart_name = frappe.db.get_value(
                'Tradeline Cart',
                {'user_id': current_user, 'status': 'Active'},
                'name'
            )
            if not cart_name:
                return {'success': False, 'error': 'No active cart found'}
            cart = frappe.get_doc('Tradeline Cart', cart_name)
        
        # Update payment mode
        cart.payment_mode = payment_mode
        cart.save()
        
        return {
            'success': True,
            'message': 'Payment mode updated successfully',
            'cart': cart.as_dict()
        }
        
    except Exception as e:
        frappe.log_error(f"Update payment mode error: {str(e)}", "Cart API Error")
        return {'success': False, 'error': str(e)}

@frappe.whitelist(allow_guest=True)
@jwt_required()
def apply_discount(discount_type, discount_value, cart_id=None):
    """Apply discount to cart"""
    try:
        current_user = get_authenticated_user()
        if not current_user:
            return {'success': False, 'error': 'Authentication required'}
        
        discount_value = flt(discount_value)
        if discount_value < 0:
            return {'success': False, 'error': 'Discount value cannot be negative'}
        
        # Get cart
        if cart_id:
            cart = frappe.get_doc('Tradeline Cart', cart_id)
            if not verify_cart_access(cart, current_user):
                return {'success': False, 'error': 'Access denied'}
        else:
            cart_name = frappe.db.get_value(
                'Tradeline Cart',
                {'user_id': current_user, 'status': 'Active'},
                'name'
            )
            if not cart_name:
                return {'success': False, 'error': 'No active cart found'}
            cart = frappe.get_doc('Tradeline Cart', cart_name)
        
        # Apply discount
        if discount_type == "amount":
            cart.discount_amount = discount_value
        elif discount_type == "percentage":
            if discount_value > 100:
                return {'success': False, 'error': 'Percentage cannot exceed 100%'}
            cart.discount_amount = (cart.subtotal * discount_value) / 100
        else:
            return {'success': False, 'error': 'Invalid discount type. Use "amount" or "percentage"'}
        
        cart.save()
        
        return {
            'success': True,
            'message': 'Discount applied successfully',
            'cart': cart.as_dict()
        }
        
    except Exception as e:
        frappe.log_error(f"Apply discount error: {str(e)}", "Cart API Error")
        return {'success': False, 'error': str(e)}

@frappe.whitelist(allow_guest=True)
@jwt_required()
def checkout_cart(cart_id=None):
    """Checkout cart and create order"""
    try:
        current_user = get_authenticated_user()
        if not current_user:
            return {'success': False, 'error': 'Authentication required'}
        
        # Get cart
        if cart_id:
            cart = frappe.get_doc('Tradeline Cart', cart_id)
            if not verify_cart_access(cart, current_user):
                return {'success': False, 'error': 'Access denied'}
        else:
            cart_name = frappe.db.get_value(
                'Tradeline Cart',
                {'user_id': current_user, 'status': 'Active'},
                'name'
            )
            if not cart_name:
                return {'success': False, 'error': 'No active cart found'}
            cart = frappe.get_doc('Tradeline Cart', cart_name)
        
        # Validate cart
        if not cart.items:
            return {'success': False, 'error': 'Cannot checkout empty cart'}
        
        if not cart.payment_mode:
            return {'success': False, 'error': 'Payment mode is required for checkout'}
        
        if not cart.customer:
            return {'success': False, 'error': 'Customer information is required for checkout'}
        
        # Process checkout
        cart.status = "Checked Out"
        cart.payment_status = "Pending"
        cart.save()
        
        # Create Sales Order (if needed)
        sales_order = None
        try:
            sales_order = create_sales_order_from_cart(cart)
        except Exception as e:
            frappe.log_error(f"Sales order creation failed: {str(e)}", "Cart Checkout Error")
        
        return {
            'success': True,
            'message': 'Checkout completed successfully',
            'cart': cart.as_dict(),
            'sales_order': sales_order.name if sales_order else None,
            'next_steps': 'Please proceed with payment processing'
        }
        
    except Exception as e:
        frappe.log_error(f"Checkout error: {str(e)}", "Cart API Error")
        return {'success': False, 'error': str(e)}

@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_cart_history(limit=20, start=0):
    """Get user's cart history"""
    try:
        current_user = get_authenticated_user()
        if not current_user:
            return {'success': False, 'error': 'Authentication required'}
        
        # Convert limit and start to integers to avoid type issues
        limit = int(limit) if limit else 20
        start = int(start) if start else 0
        
        carts = frappe.get_list(
            'Tradeline Cart',
            filters={'user_id': current_user},
            fields=['name', 'status', 'total_amount', 'payment_mode', 'payment_status', 'creation', 'modified'],
            order_by='creation desc',
            limit=limit,
            start=start
        )
        
        total_count = frappe.db.count('Tradeline Cart', {'user_id': current_user})
        
        return {
            'success': True,
            'carts': carts,
            'pagination': {
                'total': total_count,
                'limit': limit,
                'start': start,
                'has_next': (start + limit) < total_count
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Get cart history error: {str(e)}", "Cart API Error")
        return {'success': False, 'error': str(e)}

@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_payment_modes():
    """Get available payment modes"""
    try:
        payment_modes = frappe.get_list(
            'Mode of Payment',
            filters={'enabled': 1},
            fields=['name', 'mode_of_payment', 'type']
        )
        
        return {
            'success': True,
            'payment_modes': payment_modes
        }
        
    except Exception as e:
        frappe.log_error(f"Get payment modes error: {str(e)}", "Cart API Error")
        return {'success': False, 'error': str(e)}

@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_payment_methods():
    """Get available payment methods from Payment Configuration"""
    try:
        from rockettradeline.api.payment import get_payment_methods
        return get_payment_methods()
        
    except Exception as e:
        frappe.log_error(f"Get payment methods error: {str(e)}", "Cart API Error")
        return {'success': False, 'error': str(e)}

@frappe.whitelist(allow_guest=True)
@jwt_required()
def create_payment_request(payment_method, cart_id=None, **kwargs):
    """Create payment request for cart"""
    try:
        current_user = get_authenticated_user()
        if not current_user:
            return {'success': False, 'error': 'Authentication required'}
        
        # Get cart
        if cart_id:
            cart = frappe.get_doc('Tradeline Cart', cart_id)
            if not verify_cart_access(cart, current_user):
                return {'success': False, 'error': 'Access denied'}
        else:
            cart_name = frappe.db.get_value(
                'Tradeline Cart',
                {'user_id': current_user, 'status': 'Active'},
                'name'
            )
            if not cart_name:
                return {'success': False, 'error': 'No active cart found'}
            cart = frappe.get_doc('Tradeline Cart', cart_name)
        
        # Set default customer email
        if 'customer_email' not in kwargs:
            kwargs['customer_email'] = current_user
        
        # Use cart's pay method
        payment_result = cart.pay(payment_method, **kwargs)
        
        return payment_result
        
    except Exception as e:
        frappe.log_error(f"Create payment request error: {str(e)}", "Cart API Error")
        return {'success': False, 'error': str(e)}

@frappe.whitelist(allow_guest=True)
@jwt_required()
def calculate_payment_fees(amount, payment_method):
    """Calculate fees for payment"""
    try:
        from rockettradeline.api.payment import calculate_payment_fees
        return calculate_payment_fees(amount, payment_method)
        
    except Exception as e:
        frappe.log_error(f"Calculate payment fees error: {str(e)}", "Cart API Error")
        return {'success': False, 'error': str(e)}

@frappe.whitelist(allow_guest=True)
@jwt_required()
def process_cart_payment(payment_request_id, **payment_data):
    """Process payment for cart"""
    try:
        current_user = get_authenticated_user()
        if not current_user:
            return {'success': False, 'error': 'Authentication required'}
            
        from rockettradeline.api.payment import process_payment
        return process_payment(payment_request_id, **payment_data)
        
    except Exception as e:
        frappe.log_error(f"Process cart payment error: {str(e)}", "Cart API Error")
        return {'success': False, 'error': str(e)}

@frappe.whitelist(allow_guest=True)
@jwt_required()  
def get_cart_payment_status(cart_id=None):
    """Get payment status for cart"""
    try:
        current_user = get_authenticated_user()
        if not current_user:
            return {'success': False, 'error': 'Authentication required'}
        
        # Get cart
        if cart_id:
            cart = frappe.get_doc('Tradeline Cart', cart_id)
            if not verify_cart_access(cart, current_user):
                return {'success': False, 'error': 'Access denied'}
        else:
            cart_name = frappe.db.get_value(
                'Tradeline Cart',
                {'user_id': current_user, 'status': ['in', ['Active', 'Payment Pending', 'Checked Out']]},
                'name'
            )
            if not cart_name:
                return {'success': False, 'error': 'No cart found'}
            cart = frappe.get_doc('Tradeline Cart', cart_name)
        
        # Get payment requests for this cart
        payment_requests = frappe.get_all(
            'Payment Request',
            filters={'cart_id': cart.name},
            fields=['name', 'status', 'payment_method', 'total_amount', 'transaction_id', 'created_at', 'completed_at'],
            order_by='creation desc'
        )
        
        return {
            'success': True,
            'cart_status': cart.status,
            'payment_requests': payment_requests,
            'has_pending_payment': any(req['status'] == 'Pending' for req in payment_requests)
        }
        
    except Exception as e:
        frappe.log_error(f"Get cart payment status error: {str(e)}", "Cart API Error")
        return {'success': False, 'error': str(e)}

@frappe.whitelist(allow_guest=True)
@jwt_required()
def extend_cart_expiry(days=30, cart_id=None):
    """Extend cart expiry"""
    try:
        current_user = get_authenticated_user()
        if not current_user:
            return {'success': False, 'error': 'Authentication required'}
        
        days = cint(days)
        if days <= 0:
            return {'success': False, 'error': 'Days must be greater than 0'}
        
        # Get cart
        if cart_id:
            cart = frappe.get_doc('Tradeline Cart', cart_id)
            if not verify_cart_access(cart, current_user):
                return {'success': False, 'error': 'Access denied'}
        else:
            cart_name = frappe.db.get_value(
                'Tradeline Cart',
                {'user_id': current_user, 'status': 'Active'},
                'name'
            )
            if not cart_name:
                return {'success': False, 'error': 'No active cart found'}
            cart = frappe.get_doc('Tradeline Cart', cart_name)
        
        # Extend expiry
        current_expiry = cart.cart_expiry or now()
        cart.cart_expiry = add_days(current_expiry, days)
        cart.save()
        
        return {
            'success': True,
            'message': f'Cart expiry extended by {days} days',
            'new_expiry': cart.cart_expiry
        }
        
    except Exception as e:
        frappe.log_error(f"Extend cart expiry error: {str(e)}", "Cart API Error")
        return {'success': False, 'error': str(e)}

def create_sales_order_from_cart(cart):
    """Create Sales Order from cart (helper function)"""
    # This is a placeholder - implement based on your business logic
    # You might want to create Sales Order, Sales Invoice, or custom Order doctype
    
    sales_order_data = {
        'doctype': 'Sales Order',
        'customer': cart.customer,
        'delivery_date': add_days(frappe.utils.today(), 7),
        'items': [],
        'payment_terms_template': None,  # Set if you have payment terms
    }
    
    # Add items from cart
    for cart_item in cart.items:
        # Note: This assumes you have Items created for Tradelines
        # You might need to create Item records or use a different approach
        sales_order_data['items'].append({
            'item_code': cart_item.tradeline,  # This might need adjustment
            'item_name': cart_item.tradeline_name,
            'qty': cart_item.quantity,
            'rate': cart_item.rate,
            'amount': cart_item.amount
        })
    
    # Create and save
    sales_order = frappe.get_doc(sales_order_data)
    sales_order.insert()
    
    return sales_order

# Utility functions for cart management
@frappe.whitelist()
def cleanup_expired_carts():
    """Cleanup expired carts - can be run as scheduled job"""
    expired_carts = frappe.get_list(
        'Tradeline Cart',
        filters={
            'cart_expiry': ['<', now()],
            'status': ['in', ['Active', 'Abandoned']]
        },
        pluck='name'
    )
    
    for cart_id in expired_carts:
        cart = frappe.get_doc('Tradeline Cart', cart_id)
        cart.status = 'Expired'
        cart.save()
    
    return {'expired_carts_count': len(expired_carts)}

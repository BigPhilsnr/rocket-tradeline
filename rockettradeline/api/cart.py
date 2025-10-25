from rockettradeline.api.auth import jwt_required, get_current_user, get_authenticated_user
# Copyright (c) 2025, RocketTradeline and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt, now, add_days, now_datetime, get_datetime_str
import json
from rockettradeline.api.auth import jwt_required, get_current_user, get_authenticated_user

from .utils import is_administrator

def verify_cart_access(cart, current_user):
    """Verify if user has access to cart (owner or administrator)"""
    account_manager = frappe.db.get_value('Customer', dict(email_id=cart.user_id), 'account_manager')
    # frappe.throw(f'Account Manager: {account_manager} Current User: {current_user}')
    return cart.user_id == current_user or is_administrator(current_user) or (account_manager and account_manager == current_user)

def validate_cart_slots(cart):
    """
    Validate that all tradelines in cart have sufficient available slots
    Returns dict with success status and error details if validation fails
    """
    if not cart.items:
        return {'success': False, 'error': 'Cart is empty'}
    
    validation_errors = []
    
    for item in cart.items:
        try:
            # Get fresh tradeline data from database
            tradeline = frappe.get_doc('Tradeline', item.tradeline)
            
            # Check if tradeline is still active
            if tradeline.status != 'Active':
                validation_errors.append({
                    'tradeline': item.tradeline,
                    'tradeline_name': item.tradeline_name,
                    'error': f'Tradeline is no longer active (Status: {tradeline.status})'
                })
                continue
            
            # Calculate current remaining spots
            # Get all active/pending client tradelines for this tradeline (excluding current cart)
            active_client_tradelines = frappe.get_all('Client Tradelines',
                filters={
                    'tradeline': item.tradeline,
                    'status': ['in', ['Active', 'Inactive', 'Pending AU', 'Refund Requested']]
                },
                fields=['quantity']
            )
            
            total_purchased = sum(int(ct.quantity or 0) for ct in active_client_tradelines)
            current_remaining = int(tradeline.max_spots or 0) - total_purchased
            
            # Check if requested quantity exceeds available spots
            requested_quantity = int(item.quantity or 0)
            if requested_quantity > current_remaining:
                validation_errors.append({
                    'tradeline': item.tradeline,
                    'tradeline_name': item.tradeline_name,
                    'requested': requested_quantity,
                    'available': current_remaining,
                    'error': f'Insufficient slots. Requested: {requested_quantity}, Available: {current_remaining}'
                })
        
        except Exception as e:
            validation_errors.append({
                'tradeline': item.tradeline,
                'tradeline_name': item.tradeline_name,
                'error': f'Validation error: {str(e)}'
            })
    
    if validation_errors:
        return {
            'success': False,
            'error': 'Maximum slots exceeded',
            'validation_errors': validation_errors
        }
    
    return {'success': True, 'message': 'All slots are available'}

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
def get_cart(cart_id=None, status='Active Only'):
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
            # return cart_name
            if cart_name:
                print("No active cart found")
            else:
                return {'success': False, 'error': 'No active cart found', 'user': current_user}
                cart_checkout = frappe.db.get_value(
                    'Tradeline Cart',
                    {'user_id': current_user, 'status': 'Checked Out'},
                    'name'
                )
                
                if cart_checkout:
                    cart_checkout_one = frappe.db.get_value(
                    'Payment Request',
                    {'cart_id': cart_checkout, 'status': 'Pending'},
                    'cart_id'
                    )

                    if cart_checkout_one:
                        cart_name = cart_checkout_one
                    
                


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
            if cart.status != 'Active':
                frappe.throw('Cart is not active', frappe.ValidationError)
            
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
        frappe.throw(str(e), frappe.ValidationError)

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
                return {'success': False, 'error': f'Access denied for cart {cart_id} for user {current_user}'}
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
def checkout_cart(cart_id=None, address_id=None, buyer=None):
    """Checkout cart and create order"""
    try:
        current_user = get_authenticated_user()
        if not current_user:
            return {'success': False, 'error': 'Authentication required'}
        
        
        if buyer:
            if current_user != frappe.get_value('Customer', {'email_id': buyer}, 'account_manager'):
                frappe.response.http_status_code = 417
                return {'success': False, 'error': f'You are not the account manager for this buyer {frappe.get_value('Customer', {'email_id': buyer}, 'account_manager')} != {current_user}'}
        #update return with correct status code 417 instead of success false

        current_user = buyer if buyer else current_user
        
        
        # validate user status
        user_status = frappe.db.get_value('User', current_user, 'enabled')
        if not user_status:
            frappe.response.http_status_code = 417
            return {'success': False, 'error': 'User account is disabled'}
        
        # validate customer has signed agreement and filled questionnaire
        customer = frappe.db.get_value('Customer', {'email_id': current_user}, ['name', 'has_signed_agreement', 'is_questionnaire_filled'], as_dict=True)
        if not customer:
            frappe.response.http_status_code = 417
            return {'success': False, 'error': 'Customer not found'}

        if not customer.get('has_signed_agreement') and not buyer:
            frappe.response.http_status_code = 417
            return {'success': False, 'error': 'Customer has not signed the agreement'}

        if not customer.get('is_questionnaire_filled') and not buyer:
            frappe.response.http_status_code = 417
            return {'success': False, 'error': 'Customer has not filled the questionnaire'}
        
        

        # Get cart
        if cart_id:
            # frappe.db.set_value('Tradeline Cart', cart_id, 'user', current_user)
            cart = frappe.get_doc('Tradeline Cart', cart_id)
            if not verify_cart_access(cart, current_user) and not buyer:
               return {'success': False, 'error': f'Access denied for cart {cart_id} for user {current_user}'}
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
        
        # Validate slot availability before checkout
        slot_validation = validate_cart_slots(cart)
        if not slot_validation.get('success'):
            frappe.response.http_status_code = 409  # Conflict status code
            return slot_validation
        
        
        # Process checkout
        cart.status = "Checked Out"
        cart.payment_status = "Pending"
        cart.customer  = frappe.db.get_value('Customer', {'email_id': current_user}, 'name')
        cart.payment_address = address_id
        cart.user_id = buyer or current_user
        cart.save(ignore_permissions=True)
        
        
        
        return {
            'success': True,
            'message': 'Checkout completed successfully',
            'user': current_user,
            'cart': cart.as_dict(),
            # 'sales_order': sales_order.name if sales_order else None,
            'next_steps': 'Please proceed with payment processing'
        }
        
    except Exception as e:
        frappe.log_error(f"Checkout error: {str(e)}", "Cart API Error")
        return {'success': False, 'error': str(e)}

@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_carts(limit=20, start=0, status=None, user_id=None, search=None, order_by='creation desc'):
    """Get list of carts for current user or all carts if admin"""
    try:
        current_user = get_authenticated_user()
        if not current_user:
            return {'success': False, 'error': 'Authentication required'}
        
        # Convert limit and start to integers
        limit = int(limit) if limit else 20
        start = int(start) if start else 0
        
        # Check if user is administrator
        is_admin = is_administrator(current_user)
        
        # Build filters
        filters = {}
        
        if is_admin:
            # Admin can see all carts or filter by user
            if user_id:
                filters['user_id'] = user_id
        else:
            # Regular users can only see their own carts
            filters['owner'] = current_user
        
        # Add status filter if provided
        if status:
            if isinstance(status, str) and ',' in status:
                # Handle multiple statuses (comma-separated)
                status_list = [s.strip() for s in status.split(',')]
                filters['status'] = ['in', status_list]
            else:
                filters['status'] = status
        
        # Add search functionality
        search_filters = []
        if search:
            search_filters.append(['name', 'like', f'%{search}%'])
            search_filters.append(['user_id', 'like', f'%{search}%'])
            search_filters.append(['customer', 'like', f'%{search}%'])
        
        # Get cart list with detailed information
        fields = [
            'name', 'user_id', 'customer', 'status', 'payment_status',
            'subtotal', 'discount_amount', 'tax_amount', 'total_amount',
            'payment_mode', 'cart_expiry', 'creation', 'modified',
            'owner', 'modified_by'
        ]
        
        # Build query conditions
        conditions = []
        values = []
        
        # Add filters
        for key, value in filters.items():
            if isinstance(value, list) and value[0] == 'in':
                placeholders = ', '.join(['%s'] * len(value[1]))
                conditions.append(f"`{key}` IN ({placeholders})")
                values.extend(value[1])
            else:
                conditions.append(f"`{key}` = %s")
                values.append(value)
        
        # Add search conditions
        if search_filters:
            search_conditions = []
            for field, operator, search_value in search_filters:
                search_conditions.append(f"`{field}` {operator} %s")
                values.append(search_value)
            
            if search_conditions:
                conditions.append(f"({' OR '.join(search_conditions)})")
        
        # Build final query
        where_clause = ' WHERE ' + ' AND '.join(conditions) if conditions else ''
        
        # Get total count for pagination
        count_query = f"""
            SELECT COUNT(*) as total
            FROM `tabTradeline Cart`
            {where_clause}
        """
        
        total_count = frappe.db.sql(count_query, values, as_dict=True)[0]['total']
        
        # Get cart data
        data_query = f"""
            SELECT {', '.join([f'`{field}`' for field in fields])}
            FROM `tabTradeline Cart`
            {where_clause}
            ORDER BY `{order_by.replace(' desc', '').replace(' asc', '')}` {order_by.split()[-1] if ' ' in order_by else 'DESC'}
            LIMIT %s OFFSET %s
        """
        
        values.extend([limit, start])
        carts = frappe.db.sql(data_query, values, as_dict=True)
        
        # Enhance cart data with additional information
        for cart in carts:
            # Get item count for each cart
            item_count = frappe.db.count('Tradeline Cart Item', {'parent': cart['name']})
            cart['item_count'] = item_count
            
            # Get customer name if available
            if cart.get('customer'):
                customer_name = frappe.db.get_value('Customer', cart['customer'], 'customer_name')
                cart['customer_name'] = customer_name
            
            # Check if cart is expired
            if cart.get('cart_expiry'):
                cart['is_expired'] = frappe.utils.getdate(cart['cart_expiry']) < frappe.utils.getdate()
            else:
                cart['is_expired'] = False
            
            # Get latest payment request if any
            latest_payment = frappe.db.get_value(
                'Payment Request',
                {'cart_id': cart['name']},
                ['name', 'status', 'payment_method', 'transaction_id'],
                order_by='creation desc',
                as_dict=True
            )
            cart['latest_payment'] = latest_payment
        
        # Build pagination object
        current_page = (start // limit) + 1 if limit > 0 else 1
        total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
        pagination = {
            'current_page': current_page,
            'total_pages': total_pages,
            'limit': limit,
            'start': start,
            'has_next': (start + limit) < total_count,
            'has_previous': start > 0,
            'total_records': total_count
        }
        
        # Get summary statistics for admin
        summary = {}
        if is_admin:
            summary = {
                'total_carts': total_count,
                'active_carts': frappe.db.count('Tradeline Cart', {'status': 'Active'}),
                'checked_out_carts': frappe.db.count('Tradeline Cart', {'status': 'Checked Out'}),
                'expired_carts': frappe.db.count('Tradeline Cart', {'status': 'Expired'}),
                'total_revenue': frappe.db.sql("""
                    SELECT COALESCE(SUM(total_amount), 0) as total
                    FROM `tabTradeline Cart`
                    WHERE status IN ('Checked Out', 'Completed')
                """)[0][0] or 0
            }
        
        return {
            'success': True,
            'data': carts,
            'pagination': pagination,
            'summary': summary,
            'is_admin': is_admin,
            'filters_applied': {
                'status': status,
                'user_id': user_id if is_admin else current_user,
                'search': search
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Get carts error: {str(e)}", "Cart API Error")
        return {'success': False, 'error': str(e)}

@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_cart_history(limit=20, start=0):
    """Get user's cart history (legacy function - now calls get_carts)"""
    try:
        # This is now a wrapper around the more comprehensive get_carts function
        return get_carts(limit=limit, start=start, order_by='creation desc')
        
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

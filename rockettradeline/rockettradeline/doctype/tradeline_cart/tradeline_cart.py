# Copyright (c) 2025, RocketTradeline and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime, timedelta
import json

class TradelineCart(Document):
    def before_insert(self):
        """Set default values before inserting"""
        self.created_at = frappe.utils.now()
        self.modified_at = frappe.utils.now()
        
        # Set cart expiry (30 days from creation)
        if not self.cart_expiry:
            self.cart_expiry = frappe.utils.add_days(frappe.utils.now(), 30)
        
        # Get customer from user
        if self.user_id and not self.customer:
            customer = frappe.db.get_value('Customer', {'email_id': self.user_id}, 'name')
            if customer:
                self.customer = customer
    
    def before_save(self):
        """Update calculations before saving"""
        self.modified_at = frappe.utils.now()
        self.calculate_totals()
        self.validate_cart_items()
    
    def validate_cart_items(self):
        """Validate cart items"""
        # Allow empty carts in Draft and Active status (for initial creation)
        # Only require items for Checkout/Completed status
        if not self.items and self.status in ['Checkout', 'Completed']:
            frappe.throw("Cart cannot be empty for checkout")
        
        for item in self.items:
            # Validate tradeline exists and is active
            tradeline = frappe.get_doc('Tradeline', item.tradeline)
            if tradeline.status != 'Active':
                frappe.throw(f"Tradeline {item.tradeline} is not active")
            
            # Validate quantity
            if item.quantity <= 0:
                frappe.throw("Quantity must be greater than 0")
            
            # Check availability (max_spots)
            if item.quantity > tradeline.max_spots:
                frappe.throw(f"Only {tradeline.max_spots} spots available for {item.tradeline}")
    
    def calculate_totals(self):
        """Calculate cart totals"""
        subtotal = 0
        
        for item in self.items:
            if item.rate and item.quantity:
                item.amount = item.rate * item.quantity
                subtotal += item.amount
        
        self.subtotal = subtotal
        
        # Calculate total
        discount = self.discount_amount or 0
        tax = self.tax_amount or 0
        self.total_amount = subtotal - discount + tax
        
        # Return totals dictionary for API use
        return {
            'subtotal': self.subtotal,
            'discount': discount,
            'tax': tax,
            'total': self.total_amount,
            'items': [
                {
                    'tradeline': item.tradeline,
                    'tradeline_name': item.tradeline_name,
                    'quantity': item.quantity,
                    'rate': item.rate,
                    'amount': item.amount
                } for item in self.items
            ]
        }
    
    def add_item(self, tradeline_id, quantity=1):
        """Add item to cart or update quantity if exists"""
        # Check if item already exists
        existing_item = None
        for item in self.items:
            if item.tradeline == tradeline_id:
                existing_item = item
                break
        
        if existing_item:
            # Update quantity
            existing_item.quantity += quantity
        else:
            # Add new item
            tradeline = frappe.get_doc('Tradeline', tradeline_id)
            self.append('items', {
                'tradeline': tradeline_id,
                'tradeline_name': tradeline.bank,  # Assuming bank is display name
                'quantity': quantity,
                'rate': tradeline.price,
                'amount': tradeline.price * quantity
            })
        
        self.save()
        return self
    
    def remove_item(self, tradeline_id):
        """Remove item from cart"""
        for i, item in enumerate(self.items):
            if item.tradeline == tradeline_id:
                del self.items[i]
                break
        
        self.save()
        return self
    
    def update_item_quantity(self, tradeline_id, quantity):
        """Update item quantity"""
        for item in self.items:
            if item.tradeline == tradeline_id:
                if quantity <= 0:
                    return self.remove_item(tradeline_id)
                else:
                    item.quantity = quantity
                    break
        
        self.save()
        return self
    
    def clear_cart(self):
        """Clear all items from cart"""
        self.items = []
        self.save()
        return self
    
    def apply_discount(self, discount_type="amount", discount_value=0):
        """Apply discount to cart"""
        if discount_type == "amount":
            self.discount_amount = discount_value
        elif discount_type == "percentage":
            self.discount_amount = (self.subtotal * discount_value) / 100
        
        self.save()
        return self
    
    def set_payment_mode(self, payment_mode):
        """Set payment mode"""
        # Validate payment mode exists
        if not frappe.db.exists('Mode of Payment', payment_mode):
            frappe.throw(f"Payment mode {payment_mode} does not exist")
        
        self.payment_mode = payment_mode
        self.save()
        return self
    
    def pay(self, payment_method, **payment_kwargs):
        """Process payment for cart items"""
        if not self.items:
            frappe.throw("Cannot pay for empty cart")
        
        if self.status != "Active":
            frappe.throw("Cart must be active to process payment")
        
        # Import payment API to avoid circular imports
        from rockettradeline.api.payment import create_payment_request
        
        # Create payment request
        payment_result = create_payment_request(
            cart_id=self.name,
            payment_method=payment_method,
            **payment_kwargs
        )
        
        if payment_result.get("success"):
            # Update cart status to indicate payment is in progress
            self.status = "Payment Pending"
            self.payment_mode = payment_method
            self.save()
            
            return {
                'success': True,
                'payment_request_id': payment_result['payment_request_id'],
                'payment_data': payment_result['payment_data'],
                'total_amount': payment_result['total_amount'],
                'fees': payment_result['fees']
            }
        else:
            return {
                'success': False,
                'error': payment_result.get('error', 'Payment request creation failed')
            }
    
    def checkout(self):
        """Process checkout - create sales order/invoice"""
        if not self.items:
            frappe.throw("Cannot checkout empty cart")
        
        # Update status
        self.status = "Checked Out"
        self.save()
        
        # Create Sales Order (optional - for order processing)
        sales_order = self.create_sales_order()
        
        return {
            'success': True,
            'cart': self.as_dict(),
            'sales_order': sales_order.name if sales_order else None
        }
    
    def create_sales_order(self):
        """Create sales order from cart"""
        if not self.customer:
            frappe.throw("Customer is required to create sales order")
        
        # Create Sales Order
        sales_order = frappe.get_doc({
            'doctype': 'Sales Order',
            'customer': self.customer,
            'delivery_date': frappe.utils.add_days(frappe.utils.today(), 7),
            'items': []
        })
        
        # Add items
        for cart_item in self.items:
            sales_order.append('items', {
                'item_code': cart_item.tradeline,  # Assuming tradeline can be used as item
                'item_name': cart_item.tradeline_name,
                'qty': cart_item.quantity,
                'rate': cart_item.rate,
                'amount': cart_item.amount
            })
        
        # Set totals
        sales_order.total = self.subtotal
        sales_order.grand_total = self.total_amount
        
        sales_order.insert()
        sales_order.submit()
        
        return sales_order
    
    def is_expired(self):
        """Check if cart is expired"""
        if self.cart_expiry:
            return frappe.utils.now_datetime() > frappe.utils.get_datetime(self.cart_expiry)
        return False
    
    def extend_expiry(self, days=30):
        """Extend cart expiry"""
        self.cart_expiry = frappe.utils.add_days(self.cart_expiry or frappe.utils.now(), days)
        self.save()
        return self

@frappe.whitelist()
def get_cart_summary(cart_id):
    """Get cart summary with calculated totals"""
    cart = frappe.get_doc('Tradeline Cart', cart_id)
    
    return {
        'cart_id': cart.name,
        'status': cart.status,
        'item_count': len(cart.items),
        'subtotal': cart.subtotal,
        'discount_amount': cart.discount_amount,
        'tax_amount': cart.tax_amount,
        'total_amount': cart.total_amount,
        'payment_mode': cart.payment_mode,
        'expires_at': cart.cart_expiry,
        'is_expired': cart.is_expired()
    }

@frappe.whitelist()
def cleanup_expired_carts():
    """Cleanup expired carts (can be run as scheduled job)"""
    expired_carts = frappe.get_list(
        'Tradeline Cart',
        filters={
            'cart_expiry': ['<', frappe.utils.now()],
            'status': ['in', ['Active', 'Abandoned']]
        },
        pluck='name'
    )
    
    for cart_id in expired_carts:
        cart = frappe.get_doc('Tradeline Cart', cart_id)
        cart.status = 'Expired'
        cart.save()
    
    return {'expired_carts_count': len(expired_carts)}

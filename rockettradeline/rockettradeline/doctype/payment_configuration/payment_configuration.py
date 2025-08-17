# Copyright (c) 2025, RocketTradeline and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json
from decimal import Decimal

class PaymentConfiguration(Document):
    def before_insert(self):
        """Set default values before inserting"""
        if not self.display_name:
            self.display_name = self.payment_method
        
        # Set default payment type based on method
        if not self.payment_type:
            payment_types = {
                'Apple Cash': 'Digital Wallet',
                'Zelle': 'Bank Transfer',
                'CashApp': 'Peer-to-Peer',
                'Venmo': 'Peer-to-Peer',
                'PayPal': 'Digital Wallet',
                'Credit Card': 'Credit/Debit',
                'Bank Transfer': 'Bank Transfer',
                'Cryptocurrency': 'Digital Wallet'
            }
            self.payment_type = payment_types.get(self.payment_method, 'Instant')
    
    def before_save(self):
        """Validate configuration before saving"""
        self.validate_configuration()
        self.validate_fees_and_limits()
    
    def validate_configuration(self):
        """Validate payment method configuration"""
        # PayPal requires API credentials
        if self.payment_method == 'PayPal':
            if not self.sandbox_mode and not (self.api_key and self.api_secret):
                frappe.throw("PayPal requires API Key and Secret for production mode")
            elif self.sandbox_mode and not (self.sandbox_api_key and self.sandbox_api_secret):
                frappe.throw("PayPal requires Sandbox API Key and Secret for sandbox mode")
        
        # Peer-to-peer methods require account details
        if self.payment_method in ['Zelle', 'CashApp', 'Venmo']:
            if not (self.account_email or self.phone_number or self.account_id):
                frappe.throw(f"{self.payment_method} requires at least one account identifier")
        
        # Apple Cash requires phone number
        if self.payment_method == 'Apple Cash' and not self.phone_number:
            frappe.throw("Apple Cash requires a phone number")
    
    def validate_fees_and_limits(self):
        """Validate fee and limit settings"""
        if self.min_amount < 0:
            frappe.throw("Minimum amount cannot be negative")
        
        if self.max_amount <= 0:
            frappe.throw("Maximum amount must be greater than 0")
        
        if self.min_amount >= self.max_amount:
            frappe.throw("Minimum amount must be less than maximum amount")
        
        if self.fixed_fee < 0:
            frappe.throw("Fixed fee cannot be negative")
        
        if self.percentage_fee < 0 or self.percentage_fee > 100:
            frappe.throw("Percentage fee must be between 0 and 100")
    
    def calculate_fees(self, amount):
        """Calculate total fees for a given amount"""
        amount = Decimal(str(amount))
        fixed_fee = Decimal(str(self.fixed_fee or 0))
        percentage_fee = Decimal(str(self.percentage_fee or 0)) / 100
        
        total_fee = fixed_fee + (amount * percentage_fee)
        return float(total_fee)
    
    def get_payment_config(self):
        """Get payment configuration for API usage"""
        config = {
            'method': self.payment_method,
            'display_name': self.display_name,
            'type': self.payment_type,
            'is_active': self.is_active,
            'min_amount': self.min_amount,
            'max_amount': self.max_amount,
            'icon': self.icon,
            'instructions': self.instructions
        }
        
        # Add account details (safe for client-side)
        if self.account_email:
            config['account_email'] = self.account_email
        if self.phone_number:
            config['phone_number'] = self.phone_number
        if self.account_id:
            config['account_id'] = self.account_id
        if self.qr_code:
            config['qr_code'] = self.qr_code
        if self.payment_link:
            config['payment_link'] = self.payment_link
        
        return config
    
    def get_api_credentials(self):
        """Get API credentials (server-side only)"""
        if self.sandbox_mode:
            return {
                'api_key': self.sandbox_api_key,
                'api_secret': self.get_password('sandbox_api_secret'),
                'webhook_url': self.sandbox_webhook_url,
                'sandbox': True
            }
        else:
            return {
                'api_key': self.api_key,
                'api_secret': self.get_password('api_secret'),
                'webhook_url': self.webhook_url,
                'sandbox': False
            }
    
    def create_payment_request(self, amount, cart_id, customer_email=None):
        """Create a payment request for the configured method"""
        try:
            # Validate amount against limits
            if amount < self.min_amount:
                frappe.throw(f"Amount must be at least ${self.min_amount}")
            if amount > self.max_amount:
                frappe.throw(f"Amount cannot exceed ${self.max_amount}")
            
            # Calculate fees
            fees = self.calculate_fees(amount)
            total_amount = amount + fees
            
            payment_request = {
                'cart_id': cart_id,
                'payment_method': self.payment_method,
                'amount': amount,
                'fees': fees,
                'total_amount': total_amount,
                'status': 'Pending',
                'instructions': self.instructions or f"Please pay ${total_amount:.2f} using {self.display_name}"
            }
            
            # Add method-specific details
            if self.payment_method == 'PayPal':
                payment_request.update(self._create_paypal_request(total_amount, cart_id))
            elif self.payment_method in ['Zelle', 'CashApp', 'Venmo']:
                payment_request.update(self._create_p2p_request(total_amount))
            elif self.payment_method == 'Apple Cash':
                payment_request.update(self._create_apple_cash_request(total_amount))
            
            return payment_request
            
        except Exception as e:
            frappe.log_error(f"Payment request creation failed: {str(e)}")
            frappe.throw(f"Failed to create payment request: {str(e)}")
    
    def _create_paypal_request(self, amount, cart_id):
        """Create PayPal-specific payment request"""
        # This would integrate with PayPal API
        return {
            'payment_url': f"https://www.sandbox.paypal.com/checkout?amount={amount}&cart={cart_id}",
            'payment_id': f"PP-{cart_id}-{frappe.generate_hash(length=8)}",
            'instructions': f"Click the PayPal link to complete payment of ${amount:.2f}"
        }
    
    def _create_p2p_request(self, amount):
        """Create peer-to-peer payment request"""
        instructions = f"Send ${amount:.2f} to:\n"
        if self.account_email:
            instructions += f"Email: {self.account_email}\n"
        if self.phone_number:
            instructions += f"Phone: {self.phone_number}\n"
        if self.account_id:
            instructions += f"Username: {self.account_id}\n"
        if self.qr_code:
            instructions += f"Or scan the QR code to pay"
        
        return {
            'instructions': instructions,
            'qr_code': self.qr_code,
            'payment_link': self.payment_link
        }
    
    def _create_apple_cash_request(self, amount):
        """Create Apple Cash payment request"""
        return {
            'phone_number': self.phone_number,
            'instructions': f"Send ${amount:.2f} via Apple Cash to {self.phone_number}",
            'payment_link': f"https://cash.app/{self.phone_number}" if self.phone_number else None
        }

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
        
    def on_update(self):
        """Hook to send email on status change"""
        # Check if status changed to "Checked Out" or "Checkout"
        if self.has_value_changed('status') and self.status in ['Checkout', 'Checked Out']:
            frappe.msgprint("Status changed to Checked Out")
            # self.send_checkout_notification_email()
            self.send_order_received_notification()
            
            
    def validate_cart_items(self):
        """Validate cart items"""
        # Allow empty carts in Draft and Active status (for initial creation)
        # Only require items for Checked Out/Completed status
        if not self.items and self.status in ['Checked Out', 'Completed']:
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
    
    def sendcheckout_notification_email(self):
        """Send checkout notification email to customer if they have an account manager"""
        try:
            if not self.customer:
                return
            
            # Get customer document
            customer_doc = frappe.get_doc('Customer', self.customer)
            
            # Check if customer has an account manager
            if not customer_doc.account_manager:
                return
            
            # Get customer email
            customer_email = customer_doc.email_id
            if not customer_email:
                return
            
            # Get customer name (first name for personalization)
            customer_name = customer_doc.customer_name or customer_email.split('@')[0]
            first_name = customer_name.split()[0] if customer_name else "Valued Customer"
            
            # Get broker/account manager name
            broker_name = "your broker"
            try:
                broker_user = frappe.get_doc('User', customer_doc.account_manager)
                broker_name = broker_user.full_name or broker_user.first_name or customer_doc.account_manager
            except:
                pass
            
            # Use the JotForm link for the Authorized User Agreement
            signature_link = "https://www.jotform.com/sign/250833758418061/invite/01jq6t779d88b0042e02d8709f"
            
            # Prepare email subject
            subject = "Complete Your Authorized User Agreement - Rocket Tradeline"
            
            # Get email header and footer
            from rockettradeline.api.auth import get_email_header, get_email_footer
            email_header = get_email_header()
            email_footer = get_email_footer(customer_email)
            
            # Prepare email content
            message = f"""{email_header}
            <h3 style="color: #374151; margin: 0 0 20px 0;">📋 Complete Your Authorized User Agreement</h3>
            <p style="color: #374151; font-size: 16px; margin: 0 0 10px 0;">Hello {first_name},</p>
            
            <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0 0 25px 0;">
                Thank you for choosing Rocket Tradeline. Please review and complete the Authorized User Lease Agreement at the link below. This form must be signed for your order to be processed:
            </p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{signature_link}" 
                   style="background-color: #17B26A; color: white; padding: 14px 28px; text-decoration: none; 
                          border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">
                    👉 Click Here to Sign
                </a>
            </div>
            
            <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 20px; border-radius: 6px; margin: 25px 0;">
                <p style="margin: 0 0 15px 0; color: #92400e; font-weight: 600; font-size: 16px;">
                    📞 Important: Call Required for Identity Verification
                </p>
                <p style="margin: 0 0 15px 0; color: #92400e; line-height: 1.6;">
                    To proceed with your Authorized User (AU) order, we are required to verify your identity, relationship, and consent. Please call us today at <strong>469-677-7948</strong> to complete this step.
                </p>
            </div>
            
            <div style="background-color: #f0f9ff; border-left: 4px solid #17B26A; padding: 20px; border-radius: 6px; margin: 25px 0;">
                <h4 style="color: #374151; margin: 0 0 15px 0; font-size: 16px;">What this call will confirm:</h4>
                <ul style="margin: 0; padding-left: 20px; color: #6b7280; line-height: 1.6;">
                    <li style="margin: 8px 0;">✅ Your full legal name and date of birth (or last 4 of SSN).</li>
                    <li style="margin: 8px 0;">✅ That Rocket Tradeline will add you as an Authorized User to one of our cardholder accounts.</li>
                    <li style="margin: 8px 0;">✅ That your direct relationship is with Rocket Tradeline, and <strong>{broker_name}</strong> referred you.</li>
                    <li style="margin: 8px 0;">✅ That you understand you will not have access to the cardholder's account, spending privileges, or account details.</li>
                    <li style="margin: 8px 0;">✅ That you understand this service is for credit reporting purposes only.</li>
                    <li style="margin: 8px 0;">✅ That you consent to being added as an AU under these terms.</li>
                    <li style="margin: 8px 0;">✅ That you acknowledge Rocket Tradeline will remove you from the account once your agreed term has ended.</li>
                </ul>
            </div>
            
            <div style="background-color: #f9fafb; border-left: 4px solid #6b7280; padding: 15px; border-radius: 6px; margin: 25px 0;">
                <p style="margin: 0; color: #374151; font-weight: 600; font-size: 14px;">
                    📋 Next Steps:
                </p>
                <ol style="margin: 10px 0 0 0; padding-left: 20px; color: #6b7280; line-height: 1.6;">
                    <li style="margin: 5px 0;">Click the "Sign Agreement" button above</li>
                    <li style="margin: 5px 0;">Call us at 469-677-7948 for verification</li>
                    <li style="margin: 5px 0;">We'll process your AU addition once complete</li>
                </ol>
            </div>
            
            <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 25px 0 0 0;">
                Once the steps above are completed, Rocket Tradeline will proceed with your AU addition.
            </p>
            
            <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 15px 0 0 0;">
                If you have any questions, please reply directly to this email.
            </p>
            {email_footer}"""
            
            # Send email using Email Template Custom system
            try:
                from rockettradeline.rockettradeline.doctype.email_template_custom.email_template_custom import send_email_template
                
                # Prepare template parameters
                template_params = {
                    "first_name": first_name,
                    "customer_name": customer_name,
                    "broker_name": broker_name,
                    "signature_link": signature_link,
                    "customer_email": customer_email
                }
                
                # Try to use a specific template if it exists
                send_email_template(
                    template_name="Authorized User Agreement Required",
                    recipients=[customer_email],
                    parameters=template_params
                )
                
                frappe.logger().info(f"Checkout notification email sent to {customer_email} for cart {self.name}")
                
            except Exception as template_error:
                frappe.log_error(f"Template email failed for cart {self.name}: {str(template_error)}")
                
                # Fallback: Use frappe.sendmail directly
                frappe.sendmail(
                    recipients=[customer_email],
                    subject=subject,
                    message=message,
                    now=True
                )
                
                frappe.logger().info(f"Checkout notification email sent via sendmail to {customer_email} for cart {self.name}")
                
        except Exception as e:
            frappe.log_error(f"Failed to send checkout notification email for cart {self.name}: {str(e)}", "Checkout Email Error")
            # Don't raise the error to prevent cart save from failing
    
    def send_order_received_notification(self):
        """Send order received notification email to account manager or customer"""
        try:
            if not self.customer:
                return
            
            # Get customer document
            customer_doc = frappe.get_doc('Customer', self.customer)
            
            # Get customer name for subject and personalization
            customer_name = customer_doc.customer_name or customer_doc.name
            
            # Determine recipient email
            recipient_email = None
            recipient_name = "Team"
            
            # Priority: Account Manager, then Customer Email
            if customer_doc.account_manager:
                try:
                    account_manager_user = frappe.get_doc('User', customer_doc.account_manager)
                    recipient_email = account_manager_user.email
                    recipient_name = account_manager_user.full_name or account_manager_user.first_name or customer_doc.account_manager
                except:
                    # Fallback to customer email if account manager user not found
                    recipient_email = customer_doc.email_id
                    recipient_name = customer_name
            else:
                recipient_email = customer_doc.email_id
                recipient_name = customer_name
            
            if not recipient_email:
                frappe.log_error(f"No email address found for order notification - Cart: {self.name}, Customer: {self.customer}")
                return
            
            # Prepare email subject
            subject = f"Tradeline Order Received {customer_name}"
            
            # Get email header and footer
            from rockettradeline.api.auth import get_email_header, get_email_footer
            email_header = get_email_header()
            email_footer = get_email_footer(recipient_email)
            
            # Prepare email content
            message = f"""{email_header}
            <h3 style="color: #374151; margin: 0 0 20px 0;">📋 Tradeline Order Received - {customer_name}</h3>
            <p style="color: #374151; font-size: 16px; margin: 0 0 10px 0;">Hello {recipient_name.split()[0] if recipient_name else "Team"},</p>
            
            <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0 0 25px 0;">
                Thank you for submitting the Tradeline Order Form. We've received your request and are beginning the processing steps. Here's what to expect next:
            </p>
            
            <div style="background-color: #f0f9ff; border-left: 4px solid #17B26A; padding: 20px; border-radius: 6px; margin: 25px 0;">
                <h4 style="color: #374151; margin: 0 0 15px 0; font-size: 16px;">✅ Verification Call (Within 24 Hours)</h4>
                <p style="margin: 0; color: #6b7280; line-height: 1.6;">
                    A quick call will be completed with the authorized user (AU) to verify their identity, relationship, and consent.
                </p>
            </div>
            
            <div style="background-color: #f0f9ff; border-left: 4px solid #17B26A; padding: 20px; border-radius: 6px; margin: 25px 0;">
                <h4 style="color: #374151; margin: 0 0 15px 0; font-size: 16px;">✅ AU Agreement (If Not Already on File)</h4>
                <p style="margin: 0; color: #6b7280; line-height: 1.6;">
                    If we don't already have a signed AU agreement, a link will be provided for the AU to review and complete before processing continues.
                </p>
            </div>
            
            <div style="background-color: #f0f9ff; border-left: 4px solid #17B26A; padding: 20px; border-radius: 6px; margin: 25px 0;">
                <h4 style="color: #374151; margin: 0 0 15px 0; font-size: 16px;">✅ AU Confirmation (Within 24–48 Hours)</h4>
                <p style="margin: 0; color: #6b7280; line-height: 1.6;">
                    You'll receive a confirmation email once the authorized user (AU) has been successfully added to the tradeline.
                </p>
            </div>
            
            <div style="background-color: #f0f9ff; border-left: 4px solid #17B26A; padding: 20px; border-radius: 6px; margin: 25px 0;">
                <h4 style="color: #374151; margin: 0 0 15px 0; font-size: 16px;">✅ Update the AU's Address</h4>
                <p style="margin: 0; color: #6b7280; line-height: 1.6;">
                    After receiving confirmation, follow the instructions in the email to update the AU's address on their credit profile. Tools like SmartCredit or IdentityIQ can be helpful for this step.
                </p>
            </div>
            
            <div style="background-color: #f0f9ff; border-left: 4px solid #17B26A; padding: 20px; border-radius: 6px; margin: 25px 0;">
                <h4 style="color: #374151; margin: 0 0 15px 0; font-size: 16px;">✅ Reporting Timeline & Reminder</h4>
                <p style="margin: 0; color: #6b7280; line-height: 1.6;">
                    We'll send you a reminder around the tradeline's statement closing date to check whether it has posted. Please note that it may take up to two full billing cycles for the tradeline to appear on the AU's credit report.
                </p>
            </div>
            
            <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 25px 0 0 0;">
                If you have any questions in the meantime, feel free to reach out.
            </p>
            {email_footer}"""
            
            # Send email using Email Template Custom system
            try:
                from rockettradeline.rockettradeline.doctype.email_template_custom.email_template_custom import send_email_template
                
                # Send separate email for each cart item
                for item in self.items:
                    try:
                        # Get tradeline details
                        tradeline_doc = frappe.get_doc('Tradeline', item.tradeline)
                        tradeline_bank = item.tradeline_name or tradeline_doc.bank
                        credit_limit = tradeline_doc.credit_limit or 0
                        
                        # Get closing date and format with suffix
                        closing_date = tradeline_doc.closing_date or 15
                        
                        # Add ordinal suffix (st, nd, rd, th)
                        def get_ordinal_suffix(day):
                            if 10 <= day % 100 <= 20:
                                suffix = 'th'
                            else:
                                suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
                            return f"{day}{suffix}"
                        
                        reporting_date = get_ordinal_suffix(closing_date)
                        
                        # Prepare template parameters for this specific item
                        template_params = {
                            "full_name": customer_name,
                            "order_number": f"{self.name}-{item.idx}",
                            "tradeline_bank": tradeline_bank,
                            "credit_limit": credit_limit,
                            "reporting_date": reporting_date,
                            "processing_days": "5-7"
                        }
                        
                        # Send email for this specific tradeline
                        send_email_template(
                            template_name="Order Shipped",
                            recipients=[recipient_email],
                            parameters=template_params
                        )
                        
                        frappe.logger().info(f"Order notification email sent to {recipient_email} for cart {self.name}, item {item.tradeline}")
                        
                    except Exception as item_error:
                        frappe.log_error(f"Failed to send email for cart item {item.tradeline}: {str(item_error)}", "Order Item Email Error")
                        continue
                
            except Exception as template_error:
                frappe.log_error(f"Template email failed for order notification cart {self.name}: {str(template_error)}")
                
                # Fallback: Use frappe.sendmail directly
                frappe.sendmail(
                    recipients=[recipient_email],
                    subject=subject,
                    message=message,
                    now=True
                )
                
                frappe.logger().info(f"Order received notification email sent via sendmail to {recipient_email} for cart {self.name}")
                
        except Exception as e:
            frappe.log_error(f"Failed to send order received notification email for cart {self.name}: {str(e)}", "Order Notification Email Error")
            # Don't raise the error to prevent cart save from failing

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

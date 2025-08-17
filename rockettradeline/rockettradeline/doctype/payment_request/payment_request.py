# Copyright (c) 2025, RocketTradeline and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, add_days, flt
import json


class PaymentRequest(Document):
    def before_insert(self):
        """Set default values before inserting"""
        if not self.title:
            self.title = f"PAY-{self.cart_id}-{now_datetime().strftime('%Y%m%d%H%M%S')}"
        
        if not self.created_by:
            self.created_by = frappe.session.user
        
        if not self.created_at:
            self.created_at = now_datetime()
        
        # Set expiry date (24 hours from creation)
        if not self.expiry_date:
            self.expiry_date = add_days(now_datetime(), 1)
        
        # Calculate total amount if not set
        if not self.total_amount:
            self.total_amount = flt(self.amount) + flt(self.fees)
    
    def validate(self):
        """Validate payment request data"""
        self.validate_amounts()
        self.validate_cart_access()
        self.validate_payment_method()
    
    def validate_amounts(self):
        """Validate payment amounts"""
        if flt(self.amount) <= 0:
            frappe.throw("Amount must be greater than zero")
        
        if flt(self.fees) < 0:
            frappe.throw("Fees cannot be negative")
        
        expected_total = flt(self.amount) + flt(self.fees)
        if abs(flt(self.total_amount) - expected_total) > 0.01:
            frappe.throw("Total amount calculation is incorrect")
    
    def validate_cart_access(self):
        """Validate user has access to the cart"""
        if self.cart_id:
            cart = frappe.get_doc("TradelineCart", self.cart_id)
            if cart.user_id != frappe.session.user and frappe.session.user != "Administrator":
                frappe.throw("You don't have permission to create payment for this cart")
    
    def validate_payment_method(self):
        """Validate payment method is configured and active"""
        if self.payment_method:
            config = frappe.db.exists("Payment Configuration", {
                "payment_method": self.payment_method,
                "is_active": 1
            })
            if not config:
                frappe.throw(f"Payment method {self.payment_method} is not configured or inactive")
    
    def on_update(self):
        """Handle status changes"""
        if self.has_value_changed("status"):
            self.handle_status_change()
    
    def handle_status_change(self):
        """Handle payment status changes"""
        if self.status == "Completed" and not self.completed_at:
            self.completed_at = now_datetime()
        
        elif self.status == "Verified" and not self.verified_at:
            self.verified_at = now_datetime()
            if not self.verified_by:
                self.verified_by = frappe.session.user
        
        elif self.status == "Failed":
            self.send_failure_notification()
        
        elif self.status == "Expired":
            self.handle_expiry()
    
    def send_failure_notification(self):
        """Send notification when payment fails"""
        if self.customer_email:
            try:
                frappe.sendmail(
                    recipients=[self.customer_email],
                    subject=f"Payment Failed - {self.title}",
                    message=f"""
                    <p>Your payment request has failed.</p>
                    <p>Payment ID: {self.name}</p>
                    <p>Amount: ${self.total_amount}</p>
                    <p>Please contact support for assistance.</p>
                    """
                )
            except Exception as e:
                frappe.log_error(f"Failed to send payment failure email: {str(e)}")
    
    def handle_expiry(self):
        """Handle payment request expiry"""
        # Update related cart status if needed
        if self.cart_id:
            cart = frappe.get_doc("TradelineCart", self.cart_id)
            cart.add_comment("Comment", f"Payment request {self.name} expired")
    
    def get_payment_data_dict(self):
        """Get payment data as dictionary"""
        if self.payment_data:
            try:
                return json.loads(self.payment_data)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def get_payment_response_dict(self):
        """Get payment response as dictionary"""
        if self.payment_response:
            try:
                return json.loads(self.payment_response)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def update_payment_response(self, response_data):
        """Update payment response data"""
        self.payment_response = json.dumps(response_data, indent=2)
        self.save(ignore_permissions=True)
    
    def mark_as_completed(self, transaction_id=None, response_data=None):
        """Mark payment as completed"""
        self.status = "Completed"
        self.completed_at = now_datetime()
        
        if transaction_id:
            self.transaction_id = transaction_id
        
        if response_data:
            self.update_payment_response(response_data)
        
        self.save(ignore_permissions=True)
        
        # Send completion notification
        self.send_completion_notification()
    
    def send_completion_notification(self):
        """Send notification when payment is completed"""
        if self.customer_email:
            try:
                frappe.sendmail(
                    recipients=[self.customer_email],
                    subject=f"Payment Completed - {self.title}",
                    message=f"""
                    <p>Your payment has been completed successfully.</p>
                    <p>Payment ID: {self.name}</p>
                    <p>Transaction ID: {self.transaction_id}</p>
                    <p>Amount: ${self.total_amount}</p>
                    <p>Thank you for your payment!</p>
                    """
                )
            except Exception as e:
                frappe.log_error(f"Failed to send payment completion email: {str(e)}")
    
    def cancel_payment(self, reason=None):
        """Cancel payment request"""
        if self.status in ["Completed", "Verified"]:
            frappe.throw("Cannot cancel completed or verified payment")
        
        self.status = "Cancelled"
        if reason:
            self.add_comment("Comment", f"Payment cancelled: {reason}")
        
        self.save(ignore_permissions=True)
    
    def is_expired(self):
        """Check if payment request is expired"""
        if self.expiry_date:
            return now_datetime() > self.expiry_date
        return False
    
    def get_cart_details(self):
        """Get associated cart details"""
        if self.cart_id:
            return frappe.get_doc("TradelineCart", self.cart_id)
        return None
    
    def get_payment_config(self):
        """Get payment configuration for this request"""
        if self.payment_method:
            return frappe.get_doc("Payment Configuration", {
                "payment_method": self.payment_method,
                "is_active": 1
            })
        return None


# Scheduled task to handle expired payment requests
def handle_expired_payments():
    """Handle expired payment requests (called by scheduler)"""
    expired_payments = frappe.get_all(
        "Payment Request",
        filters={
            "status": ["in", ["Draft", "Pending"]],
            "expiry_date": ["<", now_datetime()]
        },
        fields=["name"]
    )
    
    for payment in expired_payments:
        try:
            doc = frappe.get_doc("Payment Request", payment.name)
            doc.status = "Expired"
            doc.save(ignore_permissions=True)
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(f"Failed to expire payment request {payment.name}: {str(e)}")

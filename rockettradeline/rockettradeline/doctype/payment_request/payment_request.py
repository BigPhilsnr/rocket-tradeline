# Copyright (c) 2025, RocketTradeline and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, add_days, flt
import json
import os
from rockettradeline.api.payment import is_administrator


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
            # Get fees from payment configuration
            if self.payment_method and self.amount:
                calculated_fees = self.calculate_fees_from_config()
                self.fees = calculated_fees.get("total_fee", 0)
            
            self.total_amount = flt(self.amount) + flt(self.fees)
        
        # Set customer information from cart or email
        self.set_customer_info()
        
        # Validate cart_id is unique
        self.validate_unique_cart_id()
    
    def validate_unique_cart_id(self):
        """Validate that cart_id is unique (no other active payment request exists for this cart)"""
        if not self.cart_id:
            return
        
        # Check for existing active payment requests for this cart
        existing_payments = frappe.get_all(
            "Payment Request",
            filters={
                "cart_id": self.cart_id,
                "status": ["not in", ["Cancelled", "Failed", "Expired", "Refunded"]],
                "name": ["!=", self.name] if self.name else ["!=", ""]
            },
            fields=["name", "status", "created_at"],
            limit=1
        )
        
        if existing_payments:
            existing_payment = existing_payments[0]
            frappe.throw(
                f"An active payment request already exists for cart {self.cart_id}. "
                f"Payment Request: {existing_payment.name} (Status: {existing_payment.status}). "
                f"Please complete or cancel the existing payment before creating a new one."
            )
    
    def calculate_fees_from_config(self):
        """Calculate fees based on payment configuration"""
        try:
            if not self.payment_method or not self.amount:
                return {"total_fee": 0}
            
            # Get payment configuration
            payment_config = frappe.get_doc("Payment Configuration", self.payment_method)
            
            # Calculate fees using the configuration
            fees_result = payment_config.calculate_fees(self.amount)
            
            # Store calculation details in payment_data
            calculation_data = {
                "fee_calculation": fees_result,
                "calculated_at": now_datetime().isoformat()
            }
            
            if self.payment_data:
                try:
                    existing_data = json.loads(self.payment_data)
                    existing_data.update(calculation_data)
                    self.payment_data = json.dumps(existing_data, indent=2)
                except json.JSONDecodeError:
                    self.payment_data = json.dumps(calculation_data, indent=2)
            else:
                self.payment_data = json.dumps(calculation_data, indent=2)
            
            return fees_result
            
        except Exception as e:
            frappe.log_error(f"Error calculating fees for payment request: {str(e)}")
            return {"total_fee": 0}
    
    def recalculate_fees(self):
        """Recalculate fees when payment method or amount changes"""
        if self.payment_method and self.amount:
            fees_result = self.calculate_fees_from_config()
            self.fees = fees_result.get("total_fee", 0)
            self.total_amount = flt(self.amount) + flt(self.fees)

    def after_insert(self):
        send_payment_approval_email(self)

    def set_customer_info(self):
        """Set customer and customer name from cart or email"""
        try:
            # First try to get customer from cart
            if self.cart_id:
                cart = frappe.get_doc("Tradeline Cart", self.cart_id)
                if cart.user_id:
                    # Try to find customer by email
                    customer = frappe.db.get_value("Customer", {"email_id": cart.user_id}, ["name", "customer_name"])
                    if customer:
                        self.customer = customer[0]
                        self.customer_name = customer[1]
                        if not self.customer_email:
                            self.customer_email = cart.user_id
                        return
            
            # If no customer found from cart, try from customer_email
            if self.customer_email and not self.customer:
                customer = frappe.db.get_value("Customer", {"email_id": self.customer_email}, ["name", "customer_name"])
                if customer:
                    self.customer = customer[0]
                    self.customer_name = customer[1]
                    return
            
            # If still no customer found, create one if we have email
            if self.customer_email and not self.customer:
                self.create_customer_from_email()
                
        except Exception as e:
            frappe.log_error(f"Error setting customer info for payment request: {str(e)}")
    
    def create_customer_from_email(self):
        """Create a new customer from email if it doesn't exist"""
        try:
            if not self.customer_email:
                return
                
            # Extract name from email (before @ symbol)
            email_name = self.customer_email.split('@')[0]
            customer_name = email_name.replace('.', ' ').replace('_', ' ').title()
            
            # Create new customer
            customer_doc = frappe.get_doc({
                "doctype": "Customer",
                "customer_name": customer_name,
                "email_id": self.customer_email,
                "customer_type": "Individual",
                "customer_group": "Individual",
                "territory": "All Territories"
            })
            
            customer_doc.insert(ignore_permissions=True)
            
            self.customer = customer_doc.name
            self.customer_name = customer_doc.customer_name
            
            frappe.logger().info(f"Created new customer {customer_doc.name} for payment request")
            
        except Exception as e:
            frappe.log_error(f"Error creating customer from email: {str(e)}")
    
    def validate(self):
        """Validate payment request data"""
        self.validate_amounts()
        self.validate_cart_access()
        self.validate_payment_method()
        
        # Validate cart_id uniqueness if changed
        if self.has_value_changed("cart_id"):
            self.validate_unique_cart_id()
        
        # Recalculate fees if payment method or amount changed
        if self.has_value_changed("payment_method") or self.has_value_changed("amount"):
            self.recalculate_fees()
    
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
            cart = frappe.get_doc("Tradeline Cart", self.cart_id)
            if cart.user_id != frappe.session.user and not is_administrator(frappe.session.user):
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
        if (self.status == "Completed" or self.approval_status == "Approved") and not self.completed_at:
            self.completed_at = now_datetime()
            # Create Client Tradelines when payment is completed
            if frappe.db.exists("Client Tradelines", {"payment_request": self.name}):
                frappe.logger().info(f"Client Tradelines already exist for payment {self.name}, skipping creation")
            else:
                self.create_client_tradelines()
    
        elif self.status == "Verified" and not self.verified_at:
            self.verified_at = now_datetime()
            if not self.verified_by:
                self.verified_by = frappe.session.user
        
        elif self.status == "Failed":
            self.send_failure_notification()
        
        elif self.status == "Expired":
            self.handle_expiry()
        
        elif self.status == "Refunded":
            self.handle_refund_status()
    
    def send_failure_notification(self):
        """Send notification when payment fails"""
        if not self.customer_email:
            return
            
        try:
            # Import email template utility
            from rockettradeline.utils.email_templates import send_email_from_template
            
            # Prepare template context with correct parameters for Payment Failed template
            context = {
                'full_name': getattr(self, 'customer_name', 'Customer'),
                'order_number': self.name,  # Payment Request ID as order number
                'amount': f"{self.total_amount:.2f}" if self.total_amount else "0.00",
                'payment_method': self.payment_method or 'N/A',
                'failure_reason': getattr(self, 'rejection_reason', None) or getattr(self, 'error_message', None) or 'Payment processing failed. Please try again or contact support.',
                'retry_payment_link': f"https://www.rockettradeline.com/buyer/payments/requests/details?request_id={self.name}",
                'support_email': 'info@rockettradeline.com'
            }
            
            # Send email using Email Template Custom
            result = send_email_from_template(
                template_name='Payment Failed',
                recipients=[self.customer_email],
                context=context
            )
            
            if result.get('success'):
                frappe.logger().info(f"Payment failure notification sent to {self.customer_email} for payment {self.name}")
                return True
            else:
                frappe.log_error(
                    f"Failed to send payment failure email to {self.customer_email}: {result.get('error')}", 
                    "Payment Failure Email Error"
                )
                return False
                
        except Exception as e:
            frappe.log_error(f"Error sending payment failure email for {self.name}: {str(e)}", "Payment Failure Email Error")
            return False
    
    def handle_expiry(self):
        """Handle payment request expiry"""
        # Update related cart status if needed
        if self.cart_id:
            cart = frappe.get_doc("Tradeline Cart", self.cart_id)
            cart.add_comment("Comment", f"Payment request {self.name} expired")
    
    def handle_refund_status(self):
        """Handle refund status change"""
        try:
            # Find Client Tradelines related to this payment request
            client_tradelines = frappe.get_all("Client Tradelines", 
                filters={"payment_request": self.name}, 
                fields=["name"])
            
            # Get proof_of_refund attachment if available
            proof_of_refund_file = None
            for tradeline in client_tradelines:
                try:
                    # Look for proof_of_refund files attached to any Client Tradeline
                    files = frappe.get_all("File", 
                        filters={
                            "attached_to_doctype": "Client Tradelines",
                            "attached_to_name": tradeline.name,
                            "file_name": ["like", "%proof_of_refund%"]
                        }, 
                        fields=["name"], 
                        limit=1)
                    
                    if files:
                        proof_of_refund_file = files[0].name
                        break
                except Exception as e:
                    frappe.logger().error(f"Error finding proof_of_refund file for Client Tradeline {tradeline.name}: {str(e)}")
            
            # Send refund notification email with attachment
            self.send_refund_notification(file_attachment=proof_of_refund_file)
            
            # Add comment to payment request
            self.add_comment("Comment", f"Refund processed. Email notification sent to {self.customer_email}")
            
        except Exception as e:
            frappe.log_error(f"Error handling refund status for payment {self.name}: {str(e)}", "Payment Refund Status Error")
    
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
    
    def send_refund_notification(self, file_attachment=None):
        """Send notification when payment is refunded"""
        if not self.customer_email:
            return
            
        try:
            # Import email functions from auth module
            from rockettradeline.api.auth import get_email_header, get_email_footer
            import os
            
            # Get consistent email header and footer
            email_header = get_email_header()
            email_footer = get_email_footer(self.customer_email)
            
            # Get cart and tradeline details
            cart_details = ""
            if self.cart_id:
                try:
                    cart = frappe.get_doc("Tradeline Cart", self.cart_id)
                    cart_items = cart.get("items", [])
                    
                    if cart_items:
                        cart_details = "<h4 style='color: #374151; margin: 20px 0 15px 0;'>Refunded Tradeline Details:</h4>"
                        cart_details += "<ul style='color: #6b7280; line-height: 1.6; margin: 0 0 20px 20px;'>"
                        
                        for item in cart_items:
                            try:
                                tradeline = frappe.get_doc("Tradeline", item.get("tradeline"))
                                bank = frappe.get_doc("Tradeline Bank", tradeline.bank) if tradeline.bank else None
                                bank_name = bank.bank_name if bank else "Unknown Bank"
                                
                                cart_details += f"<li><strong>{bank_name}</strong> - ${item.get('price', 0):.2f} x {item.get('quantity', 1)} = ${item.get('total_amount', 0):.2f}</li>"
                            except Exception:
                                cart_details += f"<li>Tradeline {item.get('tradeline', 'Unknown')} - ${item.get('total_amount', 0):.2f}</li>"
                        
                        cart_details += "</ul>"
                except Exception as e:
                    frappe.logger().error(f"Error getting cart details for refund email: {str(e)}")
            
            # Create email content
            subject = f"Refund Processed - Payment Request {self.name}"
            
            message = f"""{email_header}
            <h3 style="color: #374151; margin: 0 0 20px 0;">Refund Processed Successfully</h3>
            
            <p style="color: #6b7280; line-height: 1.6; margin: 0 0 20px 0;">
                We are writing to inform you that your refund has been processed successfully.
            </p>
            
            <div style="background-color: #f9fafb; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
                <p style="margin: 5px 0;"><strong>Payment Request ID:</strong> {self.name}</p>
                <p style="margin: 5px 0;"><strong>Original Amount:</strong> ${self.amount:.2f}</p>
                <p style="margin: 5px 0;"><strong>Refund Amount:</strong> ${self.total_amount:.2f}</p>
                <p style="margin: 5px 0;"><strong>Payment Method:</strong> {self.payment_method}</p>
                <p style="margin: 5px 0;"><strong>Cart ID:</strong> {self.cart_id}</p>
                <p style="margin: 5px 0;"><strong>Refund Date:</strong> {now_datetime().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            {cart_details}
            
            <h4 style="color: #374151; margin: 20px 0 15px 0;">What Happens Next:</h4>
            <p style="color: #6b7280; line-height: 1.6; margin: 0 0 20px 0;">
                Your refund has been processed and should appear in your {self.payment_method} account within 3-5 business days. 
                If you have any questions or concerns, please don't hesitate to contact our support team.
            </p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="mailto:support@rockettradeline.com" 
                   style="background-color: #17B26A; color: white; padding: 12px 24px; text-decoration: none; 
                          border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">
                    Contact Support
                </a>
            </div>
            {email_footer}"""
            
            # Prepare email attachments
            attachments = []
            if file_attachment:
                try:
                    file_doc = frappe.get_doc("File", file_attachment)
                    if file_doc.file_url:
                        # Get the actual file path
                        file_path = frappe.get_site_path() + file_doc.file_url
                        if os.path.exists(file_path):
                            attachments = [
                                {
                                    "fname": file_doc.file_name or "proof_of_refund",
                                    "fcontent": open(file_path, "rb").read()
                                }
                            ]
                except Exception as e:
                    frappe.logger().error(f"Error preparing refund email attachment: {str(e)}")
            
            # Send email
            frappe.sendmail(
                recipients=[self.customer_email],
                subject=subject,
                message=message,
                attachments=attachments,
                now=True
            )
            
            frappe.logger().info(f"Refund notification email sent to {self.customer_email} for payment {self.name}")
            
        except Exception as e:
            frappe.log_error(f"Error sending refund notification for payment {self.name}: {str(e)}", "Payment Refund Email Error")
    
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
            return frappe.get_doc("Tradeline Cart", self.cart_id)
        return None
    
    def get_payment_config(self):
        """Get payment configuration for this request"""
        if self.payment_method:
            return frappe.get_doc("Payment Configuration", {
                "payment_method": self.payment_method,
                "is_active": 1
            })
        return None
    
    def create_client_tradelines(self):
        """Create Client Tradelines records when payment is completed"""
        try:
            # Import here to avoid circular imports
            from rockettradeline.rockettradeline.doctype.client_tradelines.client_tradelines import create_client_tradelines_from_payment
            
            # Create Client Tradelines records
            created_records = create_client_tradelines_from_payment(self)
            
            frappe.logger().info(f"Successfully created {len(created_records)} Client Tradelines records for payment {self.name}")
            
        except Exception as e:
            frappe.log_error(f"Failed to create Client Tradelines for payment {self.name}: {str(e)}", "Payment Request Hook Error")
            # Don't raise the error to prevent payment completion from failing
            pass


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


def send_payment_approval_email(payment_request_doc):
    """Send email notification to customer when payment is approved"""
    try:
        # Import email template utility
        from rockettradeline.utils.email_templates import send_email_from_template
        
        # Get cart details
        cart = frappe.get_doc("Tradeline Cart", payment_request_doc.cart_id)
        cart_items = cart.get("items", [])
        
        # Format tradeline details HTML
        tradeline_details = ""
        if cart_items:
            tradeline_details = "<h4 style='color: #374151; margin: 20px 0 15px 0;'>Your Tradelines:</h4><ul style='margin: 0 0 20px 20px; padding: 0;'>"
            for item in cart_items:
                tradeline_details += f"<li style='margin: 5px 0; color: #6b7280;'>{item.tradeline_name} - ${item.amount:.2f}</li>"
            tradeline_details += "</ul>"
        
        # Prepare template context
        context = {
            'customer_name': getattr(payment_request_doc, 'customer_name', 'Customer'),
            'payment_request_id': payment_request_doc.name,
            'payment_method': payment_request_doc.payment_method,
            'total_amount': f"{payment_request_doc.total_amount:.2f}",
            'transaction_id': getattr(payment_request_doc, 'transaction_id', 'N/A') or 'N/A',
            'approved_at': str(getattr(payment_request_doc, 'approved_at', payment_request_doc.creation)),
            'tradeline_details': tradeline_details,
            'portal_link': 'https://rockettradeline.com'
        }
        
        # check if customer linked to the payment request has accocunt_manager, if has account manager let the email be sent to account manager
        customer = frappe.get_doc("Customer", payment_request_doc.customer)
        if customer.account_manager:
            # Send email to account manager
            result = send_email_from_template('Broker Action Required', customer.account_manager, context)
            result = send_email_from_template('Broker Action Required', payment_request_doc.customer_email, context)
        # else:
        #     print("IJ requested me to do nothing")
        #     # Send email using Email Template Custom
        #     # result = send_email_from_template('Payment Approval', payment_request_doc.customer_email, context)

        return True
        
    except Exception as e:
        frappe.log_error(f"Payment approval email error: {str(e)}")
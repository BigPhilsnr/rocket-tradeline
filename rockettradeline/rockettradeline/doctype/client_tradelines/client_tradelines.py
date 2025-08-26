# Copyright (c) 2025, RocketTradeline and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, flt


class ClientTradelines(Document):
    def before_insert(self):
        """Set default values before inserting"""
        if not self.title:
            self.title = f"CT-{self.customer}-{self.tradeline}-{now_datetime().strftime('%Y%m%d%H%M%S')}"
        
        if not self.created_date:
            self.created_date = now_datetime()
        
        # Set customer name from customer document
        if self.customer and not self.customer_name:
            customer_doc = frappe.get_doc("Customer", self.customer)
            self.customer_name = customer_doc.customer_name
        
        # Set tradeline name from tradeline document
        if self.tradeline and not self.tradeline_name:
            tradeline_doc = frappe.get_doc("Tradeline", self.tradeline)
            self.tradeline_name = f"{tradeline_doc.bank} - {tradeline_doc.credit_limit}"
        
        # Calculate total amount
        if self.quantity and self.unit_price:
            self.total_amount = flt(self.quantity) * flt(self.unit_price)
    
    def validate(self):
        """Validate client tradeline data"""
        if flt(self.quantity) <= 0:
            frappe.throw("Quantity must be greater than zero")
        
        if flt(self.unit_price) < 0:
            frappe.throw("Unit price cannot be negative")
    
    def on_update(self):
        """Handle status changes"""
        if self.has_value_changed("status"):
            self.handle_status_change()
    
    def handle_status_change(self):
        """Handle client tradeline status changes"""
        if self.status == "Completed" and not self.completion_date:
            self.completion_date = frappe.utils.today()
        
        elif self.status == "Cancelled":
            self.add_comment("Comment", f"Client tradeline cancelled on {frappe.utils.today()}")
    
    def get_cart_details(self):
        """Get associated cart details"""
        if self.cart:
            return frappe.get_doc("Tradeline Cart", self.cart)
        return None
    
    def get_payment_request_details(self):
        """Get associated payment request details"""
        if self.payment_request:
            return frappe.get_doc("Payment Request", self.payment_request)
        return None
    
    def get_tradeline_details(self):
        """Get associated tradeline details"""
        if self.tradeline:
            return frappe.get_doc("Tradeline", self.tradeline)
        return None


def create_client_tradelines_from_payment(payment_request_doc):
    """
    Create Client Tradelines records from completed payment request
    This function is called from the Payment Request hook
    """
    try:
        # Get the cart associated with the payment request
        cart = frappe.get_doc("Tradeline Cart", payment_request_doc.cart_id)
        
        # Get customer from cart
        customer = cart.customer
        customer_name = ""
        if customer:
            customer_doc = frappe.get_doc("Customer", customer)
            customer_name = customer_doc.customer_name
        
        # Loop through cart items and create Client Tradelines for each
        created_records = []
        
        for cart_item in cart.items:
            # Get tradeline details
            tradeline_doc = frappe.get_doc("Tradeline", cart_item.tradeline)
            
            # Create Client Tradelines record
            client_tradeline = frappe.get_doc({
                "doctype": "Client Tradelines",
                "customer": customer,
                "customer_name": customer_name,
                "cart": payment_request_doc.cart_id,
                "payment_request": payment_request_doc.name,
                "tradeline": cart_item.tradeline,
                "tradeline_name": f"{tradeline_doc.bank} - ${tradeline_doc.credit_limit}",
                "quantity": cart_item.quantity,
                "unit_price": cart_item.rate,
                "total_amount": cart_item.amount,
                "status": "Active",
                "created_date": now_datetime(),
                "notes": f"Created from payment request {payment_request_doc.name}"
            })
            
            client_tradeline.insert(ignore_permissions=True)
            created_records.append(client_tradeline.name)
            
            frappe.logger().info(f"Created Client Tradeline: {client_tradeline.name}")
        
        # Log successful creation
        frappe.logger().info(f"Created {len(created_records)} Client Tradelines records for payment {payment_request_doc.name}")
        
        # Add comment to payment request
        payment_request_doc.add_comment(
            "Comment", 
            f"Created {len(created_records)} Client Tradelines records: {', '.join(created_records)}"
        )
        
        return created_records
        
    except Exception as e:
        frappe.log_error(f"Error creating Client Tradelines from payment {payment_request_doc.name}: {str(e)}", "Client Tradelines Creation Error")
        raise e

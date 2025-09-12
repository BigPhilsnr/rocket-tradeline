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
    
    def after_insert(self):
        """Recalculate tradeline remaining spots after inserting new client tradeline"""
        self.recalculate_tradeline_remaining_spots()
    
    def on_trash(self):
        """Recalculate tradeline remaining spots before deleting client tradeline"""
        # Store tradeline name before deletion
        self._tradeline_for_recalc = self.tradeline
    
    def after_delete(self):
        """Recalculate tradeline remaining spots after deleting client tradeline"""
        if hasattr(self, '_tradeline_for_recalc') and self._tradeline_for_recalc:
            self.recalculate_tradeline_remaining_spots_by_tradeline(self._tradeline_for_recalc)
    
    def validate(self):
        """Validate client tradeline data"""
        if flt(self.quantity) <= 0:
            frappe.throw("Quantity must be greater than zero")
        
        if flt(self.unit_price) < 0:
            frappe.throw("Unit price cannot be negative")
    
    def on_update(self):
        """Handle status changes and recalculate tradeline remaining spots"""
        if self.has_value_changed("status"):
            self.handle_status_change()
        
        # Recalculate remaining spots for the attached tradeline when status changes
        if self.has_value_changed("status") or self.has_value_changed("quantity"):
            self.recalculate_tradeline_remaining_spots()
    
    def handle_status_change(self):
        """Handle client tradeline status changes"""
        if self.status == "Completed" and not self.completion_date:
            self.completion_date = frappe.utils.today()
        
        elif self.status == "Cancelled":
            self.add_comment("Comment", f"Client tradeline cancelled on {frappe.utils.today()}")
    
    def recalculate_tradeline_remaining_spots(self):
        """
        Recalculate remaining spots for the attached tradeline
        by summing all active client tradelines and subtracting from max spots
        """
        if not self.tradeline:
            return
        
        try:
            # Get the tradeline document
            tradeline_doc = frappe.get_doc("Tradeline", self.tradeline)
            
            # Get sum of quantities from all active client tradelines for this tradeline
            active_client_tradelines = frappe.get_all("Client Tradelines",
                filters={
                    "tradeline": self.tradeline,
                    "status": "Active"
                },
                fields=["quantity"]
            )
            
            # Calculate total purchased spots
            total_purchased_spots = sum(int(ct.quantity or 0) for ct in active_client_tradelines)
            
            # Calculate remaining spots
            max_spots = int(tradeline_doc.max_spots or 0)
            new_remaining_spots = max_spots - total_purchased_spots
            
            # Ensure remaining spots doesn't go below 0
            new_remaining_spots = max(0, new_remaining_spots)
            
            if new_remaining_spots < 1:
                frappe.throw("Error: Remaining spots cannot be negative")
            
            # Update the tradeline document only if values have changed
            if (tradeline_doc.purchased_spots != total_purchased_spots or 
                tradeline_doc.remaining_spots != new_remaining_spots):
                
                # Update fields without triggering hooks to avoid recursion
                frappe.db.set_value("Tradeline", self.tradeline, "purchased_spots", total_purchased_spots)
                frappe.db.set_value("Tradeline", self.tradeline, "remaining_spots", new_remaining_spots)
                
                # Add a comment to the tradeline about the update
                frappe.get_doc("Tradeline", self.tradeline).add_comment(
                    "Info", 
                    f"Spots recalculated: Purchased={total_purchased_spots}, Remaining={new_remaining_spots} "
                    f"(triggered by Client Tradeline {self.name} status change to '{self.status}')"
                )
                
                frappe.logger().info(
                    f"Updated Tradeline {self.tradeline}: "
                    f"purchased_spots={total_purchased_spots}, remaining_spots={new_remaining_spots}"
                )
                
        except Exception as e:
            frappe.throw(
                f"Error recalculating remaining spots for tradeline {self.tradeline} "
                f"from client tradeline {self.name}: {str(e)}", 
                "Tradeline Spots Recalculation Error"
            )
    
    def recalculate_tradeline_remaining_spots_by_tradeline(self, tradeline_name):
        """
        Recalculate remaining spots for a specific tradeline
        Used when deleting client tradelines
        """
        if not tradeline_name:
            return
        
        try:
            # Get the tradeline document
            tradeline_doc = frappe.get_doc("Tradeline", tradeline_name)
            
            # Get sum of quantities from all active client tradelines for this tradeline
            active_client_tradelines = frappe.get_all("Client Tradelines",
                filters={
                    "tradeline": tradeline_name,
                    "status": "Active"
                },
                fields=["quantity"]
            )
            
            # Calculate total purchased spots
            total_purchased_spots = sum(int(ct.quantity or 0) for ct in active_client_tradelines)
            
            # Calculate remaining spots
            max_spots = int(tradeline_doc.max_spots or 0)
            new_remaining_spots = max_spots - total_purchased_spots
            
            # Ensure remaining spots doesn't go below 0
            new_remaining_spots = max(0, new_remaining_spots)
            
            # Update the tradeline document
            frappe.db.set_value("Tradeline", tradeline_name, "purchased_spots", total_purchased_spots)
            frappe.db.set_value("Tradeline", tradeline_name, "remaining_spots", new_remaining_spots)
            
            # Add a comment to the tradeline about the update
            frappe.get_doc("Tradeline", tradeline_name).add_comment(
                "Info", 
                f"Spots recalculated after client tradeline deletion: "
                f"Purchased={total_purchased_spots}, Remaining={new_remaining_spots}"
            )
            
            frappe.logger().info(
                f"Updated Tradeline {tradeline_name} after deletion: "
                f"purchased_spots={total_purchased_spots}, remaining_spots={new_remaining_spots}"
            )
            
        except Exception as e:
            frappe.log_error(
                f"Error recalculating remaining spots for tradeline {tradeline_name} "
                f"after client tradeline deletion: {str(e)}", 
                "Tradeline Spots Recalculation Error"
            )
    
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

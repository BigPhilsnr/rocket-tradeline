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
            
    def swap(self, new_tradeline):
        """Swap the tradeline associated with this client tradeline"""
        if not new_tradeline:
            frappe.throw("New tradeline must be specified for swap")
        
        old_tradeline = self.tradeline
        # if old_tradeline == new_tradeline:
        #     frappe.throw("New tradeline must be different from the current tradeline")
        
        # Update to new tradeline
        self.tradeline = new_tradeline
        
        # Update tradeline name
        tradeline_doc = frappe.get_doc("Tradeline", new_tradeline)
        self.tradeline_name = f"{tradeline_doc.bank} - {tradeline_doc.credit_limit}"
        self.swapped = 1
        self.swapped_on = now_datetime()
        self.expiry_date = None  # Reset expiry date on swap
        self.status ="Pending AU"
        
        self.save(ignore_permissions=True)
        
        # Recalculate remaining spots for both old and new tradelines
        self.recalculate_tradeline_remaining_spots_by_tradeline(old_tradeline)
        self.recalculate_tradeline_remaining_spots_by_tradeline(new_tradeline)
        
        return f"Client Tradeline {self.name} swapped to Tradeline {new_tradeline} successfully"
    
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
        if self.has_value_changed("status") or (self.has_value_changed("quantity") and self.status != "Refund Requested"):
            self.recalculate_tradeline_remaining_spots()
    
    def handle_status_change(self):
        """Handle client tradeline status changes"""
        if self.status == "Completed" and not self.completion_date:
            self.completion_date = frappe.utils.today()
        
        elif self.status == "Cancelled":
            self.add_comment("Comment", f"Client tradeline cancelled on {frappe.utils.today()}")
        
        elif self.status == "Pending AU":
            # Send AU assignment notification email to cardholder
            try:
                self.send_au_assignment_email()
                frappe.logger().info(f"AU assignment notification processed for client tradeline {self.name}")
            except Exception as e:
                frappe.log_error(
                    f"Failed to send AU assignment notification for client tradeline {self.name}: {str(e)}", 
                    "AU Assignment Notification Error"
                )
        
        elif self.status == "Refund Requested":
            # Send refund request notification email to admin
            try:
                self.send_refund_request_notification_email()
                frappe.logger().info(f"Refund request notification processed for client tradeline {self.name}")
            except Exception as e:
                frappe.log_error(
                    f"Failed to send refund request notification for client tradeline {self.name}: {str(e)}", 
                    "Refund Request Notification Error"
                )
        
        elif self.status == "Active":
            # Send active status notification email to customer
            try:
                self.send_active_status_notification_email()
                print(f"Active status notification processed for client tradeline {self.name}")
            except Exception as e:
                frappe.log_error(
                    f"Failed to send active status notification for client tradeline {self.name}: {str(e)}", 
                    "Active Status Notification Error"
                )
        
        elif self.status == "Removed":
            # Send removal confirmation email to customer
            try:
                self.send_removal_confirmation_email()
                print(f"Removal confirmation notification processed for client tradeline {self.name}")
            except Exception as e:
                frappe.log_error(
                    f"Failed to send removal confirmation notification for client tradeline {self.name}: {str(e)}", 
                    "Removal Confirmation Notification Error"
                )
    
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
            
            # Get sum of quantities from all active and inactive client tradelines for this tradeline
            active_client_tradelines = frappe.get_all("Client Tradelines",
                filters={
                    "tradeline": self.tradeline,
                    "status": ["in", ["Active", "Inactive", "Pending AU", "Refund Requested"]]
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
    
    def send_au_assignment_email(self):
        """
        Send AU assignment notification email to the cardholder
        This method gathers all required data and sends the email using the AU Assignment template
        """
        try:
            # Get the tradeline details
            tradeline_doc = frappe.get_doc("Tradeline", self.tradeline)
            
            # Get the cardholder (who receives the email)
            cardholder_doc = frappe.get_doc("Customer", tradeline_doc.card_holder)
            
            # Get the AU customer details (who is being added)
            au_customer_doc = frappe.get_doc("Customer", self.customer)
            
            # Get bank information
            bank_doc = frappe.get_doc("Tradeline Bank", tradeline_doc.bank) if tradeline_doc.bank else None
            
            # Get cardholder's first name
            cardholder_full_name = cardholder_doc.customer_name or ""
            cardholder_first_name = cardholder_full_name.split()[0] if cardholder_full_name else "Valued Customer"
            
            # Get AU customer details
            au_full_name = au_customer_doc.customer_name or ""
            au_name_parts = au_full_name.split()
            au_first_name = au_name_parts[0] if au_name_parts else "Customer"
            au_last_initial = au_name_parts[-1][0] if len(au_name_parts) > 1 else "X"
            
            # Get AU customer date of birth (MM/DD format)
            au_dob = "MM/DD"  # Default if no DOB available
            if hasattr(au_customer_doc, 'date_of_birth') and au_customer_doc.date_of_birth:
                from frappe.utils import formatdate
                au_dob = formatdate(au_customer_doc.date_of_birth, "MM/dd")
            
            # Get AU SSN last 4 digits
            au_ssn_last_4 = "XXXX"  # Default masked value
            if hasattr(au_customer_doc, 'tax_id') and au_customer_doc.tax_id:
                au_ssn_last_4 = str(au_customer_doc.tax_id)[-4:] if len(str(au_customer_doc.tax_id)) >= 4 else "XXXX"
            
            # Calculate year opened from tradeline age
            from datetime import datetime
            current_year = datetime.now().year
            year_opened = current_year - (tradeline_doc.age_year or 0)
            
            # Format closing date (MM/DD format)
            closing_date = "MM/DD"
            if tradeline_doc.closing_date:
                from frappe.utils import formatdate
                closing_date = formatdate(tradeline_doc.closing_date, "MM/dd")
            
            # Calculate payment amount (unit price for this client tradeline)
            payment_amount = f"{float(self.unit_price or 0):.2f}"
            
            # Prepare context for the email template
            context = {
                'cardholder_first_name': cardholder_first_name,
                'au_first_name': au_first_name,
                'au_last_initial': au_last_initial,
                'au_dob': au_dob,
                'au_ssn_last_4': au_ssn_last_4,
                'year_opened':tradeline_doc.age_year,
                'bank_name':  tradeline_doc.bank,
                'credit_limit': f"{float(tradeline_doc.credit_limit or 0):,.0f}",
                'closing_date': closing_date,
                'payment_amount': tradeline_doc.commission,
                'cardholder_login_link': 'https://rocket-app.tiberbuhealth.com/cardholder-portal'
            }
            
            # Send the email using the template
            from rockettradeline.utils.email_templates import send_email_from_template
            
            result = send_email_from_template(
                template_name='AU Assignment Notification',
                recipients=[cardholder_doc.email_id],
                context=context
            )
            
            if result.get('success'):
                # Add a comment to the client tradeline about the email sent
                self.add_comment(
                    "Info", 
                    f"AU assignment notification email sent to cardholder {cardholder_doc.email_id} "
                    f"for AU {au_first_name} {au_last_initial}."
                )
                frappe.logger().info(
                    f"AU assignment email sent successfully to {cardholder_doc.email_id} "
                    f"for client tradeline {self.name}"
                )
                return True
            else:
                frappe.log_error(
                    f"Failed to send AU assignment email to {cardholder_doc.email_id} "
                    f"for client tradeline {self.name}: {result.get('error')}", 
                    "AU Assignment Email Error"
                )
                return False
                
        except Exception as e:
            frappe.log_error(
                f"Error sending AU assignment email for client tradeline {self.name}: {str(e)}", 
                "AU Assignment Email Error"
            )
            return False

    def send_refund_request_notification_email(self):
        """
        Send refund request notification email to admin
        This method gathers all required data and sends the email using the Refund Request template
        """
        try:
            # Get the tradeline details
            tradeline_doc = frappe.get_doc("Tradeline", self.tradeline)
            
            # Get the customer details (who is requesting refund)
            customer_doc = frappe.get_doc("Customer", self.customer)
            
            # Get bank information
            bank_doc = frappe.get_doc("Tradeline Bank", tradeline_doc.bank) if tradeline_doc.bank else None
            
            # Calculate tradeline age for display
            age_display = f"{tradeline_doc.age_year or 0} years"
            if tradeline_doc.age_month:
                age_display += f", {tradeline_doc.age_month} months"
            
            # Format dates
            request_date = frappe.utils.now()
            purchase_date = self.created_date or self.creation
            completion_date = self.completion_date or "N/A"
            expiry_date = self.expiry_date or "N/A"
            last_modified = self.modified
            
            # Get requesting user (could be admin or customer)
            requesting_user = frappe.session.user
            try:
                requesting_user_doc = frappe.get_doc("User", requesting_user)
                requesting_user_name = requesting_user_doc.full_name or requesting_user
            except:
                requesting_user_name = requesting_user
            
            # Format phone number
            customer_phone = getattr(customer_doc, 'mobile_no', None) or getattr(customer_doc, 'phone', None) or "N/A"
            
            # Prepare context for the email template
            context = {
                'client_tradeline_id': self.name,
                'request_date': str(request_date),
                'requesting_user': requesting_user_name,
                'previous_status': self._doc_before_save.status if hasattr(self, '_doc_before_save') else "Unknown",
                'refund_reason': self.refund_reason or "No specific reason provided",
                'customer_id': self.customer,
                'customer_name': customer_doc.customer_name or "N/A",
                'customer_email': customer_doc.email_id or "N/A",
                'customer_phone': customer_phone,
                'tradeline_id': self.tradeline,
                'tradeline_name': self.tradeline_name,
                'bank_name': bank_doc.bank_name if bank_doc else tradeline_doc.bank,
                'credit_limit': f"{float(tradeline_doc.credit_limit or 0):,.0f}",
                'tradeline_age': age_display,
                'quantity': str(self.quantity or 1),
                'unit_price': f"{float(self.unit_price or 0):.2f}",
                'total_amount': f"{float(self.total_amount or 0):.2f}",
                'payment_request_id': self.payment_request or "N/A",
                'cart_id': self.cart or "N/A",
                'purchase_date': str(purchase_date),
                'completion_date': str(completion_date),
                'expiry_date': str(expiry_date),
                'last_modified': str(last_modified),
                'refund_username': self.refund_username or "N/A",
                'refund_security_question': self.refund_security_question or "N/A",
                'refund_security_answer': self.refund_security_answer or "N/A",
                'refund_pin': self.refund_pin or "N/A",
                'refund_link': self.refund_link or "N/A"
            }
            
            # Send the email using the template
            from rockettradeline.utils.email_templates import send_email_from_template
            
            result = send_email_from_template(
                template_name='Refund Request Notification',
                recipients=["info@rockettradeline.com"],
                context=context
            )
            
            if result.get('success'):
                # Add a comment to the client tradeline about the email sent
                self.add_comment(
                    "Info", 
                    f"Refund request notification email sent to admin for customer {customer_doc.customer_name} "
                    f"({customer_doc.email_id}). Reason: {self.refund_reason or 'No reason provided'}"
                )
                frappe.logger().info(
                    f"Refund request notification email sent successfully for client tradeline {self.name}"
                )
                return True
            else:
                frappe.log_error(
                    f"Failed to send refund request notification email for client tradeline {self.name}: {result.get('error')}", 
                    "Refund Request Email Error"
                )
                return False
                
        except Exception as e:
            frappe.log_error(
                f"Error sending refund request notification email for client tradeline {self.name}: {str(e)}", 
                "Refund Request Email Error"
            )
            return False

    def send_active_status_notification_email(self):
        """
        Send active status notification email to customer
        This method gathers all required data and sends the email using the Active Status template
        """
        try:
            # Get the tradeline details
            tradeline_doc = frappe.get_doc("Tradeline", self.tradeline)
            
            # Get the customer details (who receives the email)
            customer_doc = frappe.get_doc("Customer", self.customer)
            
            # Get bank information
            bank_doc = frappe.get_doc("Tradeline Bank", tradeline_doc.bank) if tradeline_doc.bank else None
            
            # Calculate year opened from tradeline age
            from datetime import datetime
            current_year = datetime.now().year
            year_opened = current_year - (tradeline_doc.age_year or 0)
            
            # Format closing date (day only)
            closing_day = "25th"  # Default
            if tradeline_doc.closing_date:
                from frappe.utils import formatdate
                day = int(formatdate(tradeline_doc.closing_date, "dd"))
                if day == 1:
                    closing_day = "1st"
                elif day == 2:
                    closing_day = "2nd"
                elif day == 3:
                    closing_day = "3rd"
                else:
                    closing_day = f"{day}th"
            
            # Get customer name parts
            customer_full_name = customer_doc.customer_name or "Customer"
            customer_name_parts = customer_full_name.split()
            customer_first_name = customer_name_parts[0] if customer_name_parts else "Customer"
            customer_last_name = customer_name_parts[-1] if len(customer_name_parts) > 1 else ""
            
            # Format credit limit in K format
            credit_limit_k = f"${float(tradeline_doc.credit_limit or 0)/1000:.1f}K" if tradeline_doc.credit_limit else "$0K"
            
            # Prepare context for the email template
            context = {
                'customer_name': customer_full_name,
                'customer_first_name': customer_first_name,
                'customer_last_name': customer_last_name,
                'au_name': customer_full_name,  # Same as customer for AU name
                'year_opened': str(year_opened),
                'bank_name': bank_doc.bank_name if bank_doc else tradeline_doc.bank,
                'credit_limit_k': credit_limit_k,
                'closing_day': closing_day,
                'tradeline_info': f"{year_opened}, {bank_doc.bank_name if bank_doc else tradeline_doc.bank}, {credit_limit_k}, {closing_day}",
                'mailing_address': '195 E ROUND GROVE RD, APT 2423, LEWISVILLE, TX 75067'
            }
            
            # Send the email using the template
            from rockettradeline.utils.email_templates import send_email_from_template
            
            result = send_email_from_template(
                template_name='Active Status Notification',
                recipients=[customer_doc.email_id],
                context=context
            )
            
            if result.get('success'):
                # Add a comment to the client tradeline about the email sent
                self.add_comment(
                    "Info", 
                    f"Active status notification email sent to customer {customer_doc.customer_name} "
                    f"({customer_doc.email_id}) for tradeline activation."
                )
                print(
                    f"Active status notification email sent successfully to {customer_doc.email_id} "
                    f"for client tradeline {self.name}"
                )
                return True
            else:
                frappe.log_error(
                    f"Failed to send active status notification email to {customer_doc.email_id} "
                    f"for client tradeline {self.name}: {result.get('error')}", 
                    "Active Status Email Error"
                )
                return False
                
        except Exception as e:
            frappe.log_error(
                f"Error sending active status notification email for client tradeline {self.name}: {str(e)}", 
                "Active Status Email Error"
            )
            return False

    def send_removal_confirmation_email(self):
        """
        Send removal confirmation email to customer
        This method gathers all required data and sends the email using the Removal Confirmation template
        """
        try:
            # Get the tradeline details
            tradeline_doc = frappe.get_doc("Tradeline", self.tradeline)
            
            # Get the customer details (who receives the email)
            customer_doc = frappe.get_doc("Customer", self.customer)
            
            # Get bank information
            bank_doc = frappe.get_doc("Tradeline Bank", tradeline_doc.bank) if tradeline_doc.bank else None
            
            # Calculate year opened from tradeline age
            from datetime import datetime
            current_year = datetime.now().year
            year_opened = current_year - (tradeline_doc.age_year or 0)
            
            # Get customer name
            customer_full_name = customer_doc.customer_name or "Customer"
            
            # Format credit limit
            credit_limit_formatted = f"${float(tradeline_doc.credit_limit or 0):,.0f}" if tradeline_doc.credit_limit else "$0"
            
            # Prepare context for the email template
            context = {
                'customer_name': customer_full_name,
                'au_name': customer_full_name,  # Same as customer for AU name
                'bank_name': bank_doc.bank_name if bank_doc else tradeline_doc.bank,
                'year_opened': str(year_opened),
                'credit_limit': credit_limit_formatted,
                'tradeline_info': f"{bank_doc.bank_name if bank_doc else tradeline_doc.bank} {year_opened} {credit_limit_formatted}"
            }
            
            # Send the email using the template
            from rockettradeline.utils.email_templates import send_email_from_template
            
            result = send_email_from_template(
                template_name='Removal Confirmation',
                recipients=[customer_doc.email_id],
                context=context
            )
            
            if result.get('success'):
                # Add a comment to the client tradeline about the email sent
                self.add_comment(
                    "Info", 
                    f"Removal confirmation email sent to customer {customer_doc.customer_name} "
                    f"({customer_doc.email_id}) for tradeline removal confirmation."
                )
                print(
                    f"Removal confirmation email sent successfully to {customer_doc.email_id} "
                    f"for client tradeline {self.name}"
                )
                return True
            else:
                frappe.log_error(
                    f"Failed to send removal confirmation email to {customer_doc.email_id} "
                    f"for client tradeline {self.name}: {result.get('error')}", 
                    "Removal Confirmation Email Error"
                )
                return False
                
        except Exception as e:
            frappe.log_error(
                f"Error sending removal confirmation email for client tradeline {self.name}: {str(e)}", 
                "Removal Confirmation Email Error"
            )
            return False


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
                "status": "Pending AU",
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

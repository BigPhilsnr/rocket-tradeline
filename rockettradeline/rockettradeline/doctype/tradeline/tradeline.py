# Copyright (c) 2025, philmaxsnr@gmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, get_url_to_form
from rockettradeline.api.auth import get_email_header, get_email_footer


class Tradeline(Document):
	def on_update(self):
		"""Hook called when tradeline is updated"""
		if self.has_value_changed("status"):
			self.handle_status_change()
	
	def handle_status_change(self):
		"""Handle status change and send notifications"""
		old_status = self.get_doc_before_save().status if self.get_doc_before_save() else None
		new_status = self.status
		
		# Send notification when tradeline is activated (InActive -> Active)
		if old_status == "InActive" and new_status == "Active":
			self.send_activation_notification()
	
	def send_activation_notification(self):
		"""Send email notification to card holder when tradeline is activated"""
		try:
			if not self.card_holder:
				return
			
			# Get customer details
			customer_doc = frappe.get_doc("Customer", self.card_holder)
			if not customer_doc.email_id:
				frappe.log_error(f"No email found for customer {self.card_holder}")
				return
			
			# Get bank name for better email content
			bank_name = "Unknown Bank"
			if self.bank:
				try:
					bank_doc = frappe.get_doc("Tradeline Bank", self.bank)
					bank_name = bank_doc.bank_name
				except:
					pass
			
			# Get consistent email header and footer
			email_header = get_email_header()
			email_footer = get_email_footer(customer_doc.email_id)
			
			# Prepare email content
			subject = f"Tradeline Activated - {bank_name}"
			
			# Get tradeline URL for reference
			tradeline_url = get_url_to_form("Tradeline", self.name)
			
			message = f"""{email_header}
			<h3 style="color: #17B26A; margin: 0 0 20px 0;">Your Tradeline Has Been Activated!</h3>
			<p style="color: #374151; font-size: 16px; margin: 0 0 10px 0;">Dear {customer_doc.customer_name or customer_doc.name},</p>
			
			<p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0 0 25px 0;">
				Great news! Your tradeline has been successfully activated and is now available for purchase by clients.
			</p>
			
			<h4 style="color: #374151; margin: 20px 0 15px 0;">Tradeline Details:</h4>
			<div style="background-color: #f9fafb; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
				<p style="margin: 5px 0;"><strong>Tradeline ID:</strong> {self.name}</p>
				<p style="margin: 5px 0;"><strong>Bank:</strong> {bank_name}</p>
				<p style="margin: 5px 0;"><strong>Credit Limit:</strong> ${self.credit_limit:,}</p>
				<p style="margin: 5px 0;"><strong>Price:</strong> ${self.price}</p>
				<p style="margin: 5px 0;"><strong>Available Spots:</strong> {self.remaining_spots}/{self.max_spots}</p>
				<p style="margin: 5px 0;"><strong>Closing Date:</strong> {self.closing_date}</p>
				<p style="margin: 5px 0;"><strong>Age:</strong> {self.age_year} years {self.age_month or 0} months</p>
				<p style="margin: 5px 0;"><strong>Status:</strong> Active</p>
			</div>
			
			<h4 style="color: #374151; margin: 20px 0 15px 0;">What's Next:</h4>
			<ul style="margin: 0 0 25px 20px; padding: 0; color: #6b7280; line-height: 1.6;">
				<li style="margin: 5px 0;">Your tradeline is now visible to potential buyers</li>
				<li style="margin: 5px 0;">You'll receive notifications when clients purchase spots</li>
				<li style="margin: 5px 0;">Monitor your tradeline performance in the seller portal</li>
				<li style="margin: 5px 0;">Payments will be processed according to your agreement</li>
			</ul>
			
			<div style="text-align: center; margin: 30px 0;">
				<a href="{tradeline_url}" 
				   style="background-color: #17B26A; color: white; padding: 12px 24px; text-decoration: none; 
						  border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">
					View Your Tradeline
				</a>
			</div>
			
			<p style="color: #6b7280; margin: 25px 0 0 0; font-size: 16px;">
				Thank you for choosing RocketTradeline as your tradeline partner!
			</p>
			{email_footer}"""
			
			# Send email
			frappe.sendmail(
				recipients=[customer_doc.email_id],
				subject=subject,
				message=message,
				header=["Tradeline Activation", "green"]
			)
			
			# Log the notification
			frappe.logger().info(f"Tradeline activation notification sent to {customer_doc.email_id} for tradeline {self.name}")
			
		except Exception as e:
			frappe.log_error(f"Failed to send tradeline activation notification: {str(e)}", "Tradeline Activation Email Error")

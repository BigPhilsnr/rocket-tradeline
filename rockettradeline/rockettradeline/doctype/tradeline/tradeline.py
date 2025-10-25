# Copyright (c) 2025, philmaxsnr@gmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, get_url_to_form
from rockettradeline.api.auth import get_email_header, get_email_footer


class Tradeline(Document):

	def after_insert(self):
		self.send_admin_review_email()

	def on_update(self):
		"""Hook called when tradeline is updated"""

		if self.has_value_changed("status"):
			self.handle_status_change()
		self.recalculate_tradeline_remaining_spots()

	def send_admin_review_email(self):
		"""Send email to all administrators when a tradeline is created for review"""
		try:
			# Find all users with role_profile_name = 'Administrator'
			admin_users = frappe.get_all("User", filters={"role_profile_name": "Administrator", "enabled": 1}, fields=["name"])
			admin_emails = [u["name"] for u in admin_users if u["name"]]
			if not admin_emails:
				frappe.log_error("No administrator emails found.", "Tradeline Admin Review Email Error")
				return

			# Get consistent email header and footer
			email_header = get_email_header()
			email_footer = get_email_footer(admin_emails[0])

			subject = f"New Tradeline Created for Review - {self.name}"
			tradeline_url = "https://www.rockettradeline.com/admin/tradelines-inventory"  # Default URL

			message = f"""{email_header}
			<h3 style='color: #1D4ED8; margin: 0 0 20px 0;'>New Tradeline Created for Review</h3>
			<p style='color: #374151; font-size: 16px; margin: 0 0 10px 0;'>A new tradeline has been created and requires your review:</p>
			<div style='background-color: #f9fafb; padding: 20px; border-radius: 6px; margin-bottom: 25px;'>
				<p style='margin: 5px 0;'><strong>Tradeline ID:</strong> {self.name}</p>
				<p style='margin: 5px 0;'><strong>Card Holder:</strong> {self.card_holder}</p>
				<p style='margin: 5px 0;'><strong>Bank:</strong> {self.bank}</p>
				<p style='margin: 5px 0;'><strong>Credit Limit:</strong> ${self.credit_limit:,}</p>
				<p style='margin: 5px 0;'><strong>Price:</strong> ${self.price}</p>
				<p style='margin: 5px 0;'><strong>Available Spots:</strong> {self.remaining_spots}/{self.max_spots}</p>
				<p style='margin: 5px 0;'><strong>Closing Date:</strong> {self.closing_date}</p>
				<p style='margin: 5px 0;'><strong>Age:</strong> {self.age_year} years {self.age_month or 0} months</p>
				<p style='margin: 5px 0;'><strong>Status:</strong> {self.status}</p>
			</div>
			<div style='text-align: center; margin: 30px 0;'>
				<a href='{tradeline_url}'
					style='background-color: #1D4ED8; color: white; padding: 12px 24px; text-decoration: none;
						border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;'>
					Review Tradeline
				</a>
			</div>
			<p style='color: #6b7280; margin: 25px 0 0 0; font-size: 16px;'>
				Please review and approve or reject this tradeline in the admin portal.
			</p>
			{email_footer}"""

			frappe.sendmail(
				recipients=admin_emails,
				subject=subject,
				message=message,
				delayed=False,
				header=["Tradeline Review", "blue"]
			)
			frappe.logger().info(f"Tradeline review notification sent to administrators for tradeline {self.name}")
		except Exception as e:
			frappe.log_error(f"Failed to send tradeline review notification: {str(e)}", "Tradeline Admin Review Email Error")

	def handle_status_change(self):
		"""Handle status change and send notifications"""
		old_status = self.get_doc_before_save().status if self.get_doc_before_save() else None
		new_status = self.status

		# Send notification when tradeline is activated (InActive -> Active)
		if old_status == "InActive" and new_status == "Active":
			self.send_activation_notification()

	def recalculate_tradeline_remaining_spots(self):
		"""
		Recalculate remaining spots for the attached tradeline
		by summing all active client tradelines and subtracting from max spots
		"""
		if not self.name:
			return

		try:
			# Get the tradeline document
			tradeline_doc = frappe.get_doc("Tradeline", self.name)

			# Get sum of quantities from all active and inactive client tradelines for this tradeline
			active_client_tradelines = frappe.get_all("Client Tradelines",
				filters={
					"tradeline": tradeline_doc.name,
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
				frappe.db.set_value("Tradeline", self.name, "purchased_spots", total_purchased_spots)
				frappe.db.set_value("Tradeline", self.name, "remaining_spots", new_remaining_spots)

				# Add a comment to the tradeline about the update
				frappe.get_doc("Tradeline", self.name).add_comment(
					"Info",
					f"Spots recalculated: Purchased={total_purchased_spots}, Remaining={new_remaining_spots} "
					f"(triggered by Tradeline {self.name} status change to '{self.status}')"
				)

				frappe.logger().info(
					f"Updated Tradeline {self.name}: "
					f"purchased_spots={total_purchased_spots}, remaining_spots={new_remaining_spots}"
				)

		except Exception as e:
			frappe.throw(
				f"Error recalculating remaining spots for tradeline {self.name}: {str(e)}",
				"Tradeline Spots Recalculation Error"
			)

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
				Thank you for choosing Rocket Tradeline as your tradeline partner!
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

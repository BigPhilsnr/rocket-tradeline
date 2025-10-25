# Copyright (c) 2025, RocketTradeLine and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
import time
from datetime import datetime


class TradelineImport(Document):
	"""
	Main DocType for importing historical tradeline purchases.
	
	Groups items by customer email and processes each group:
	1. User (if doesn't exist) - one per customer
	2. Customer (with is_external=1) - one per customer
	3. Tradeline Cart (with is_external=1) - one per customer, contains all items
	4. Payment Request (with is_external=1) - one per customer
	5. Client Tradelines (with is_external=1) - one per import item
	
	Items with the same customer email share a single cart and payment request.
	Each import item creates exactly ONE Client Tradeline record.
	All emails are suppressed if suppress_emails is checked.
	"""
	
	def validate(self):
		"""Validate the import data before submission"""
		# Auto-generate import title if not provided
		if not self.import_title:
			self.import_title = f"Historical Tradeline Import - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
		
		self.total_records = len(self.import_items)
		
		# Reset processing fields
		self.successful_imports = 0
		self.failed_imports = 0
		self.validation_log = ""
		self.processing_log = ""
		
		# Validate each import item
		validation_errors = []
		for idx, item in enumerate(self.import_items, start=1):
			errors = self.validate_import_item(item, idx)
			if errors:
				validation_errors.extend(errors)
		
		if validation_errors:
			self.validation_log = "\n".join(validation_errors)
			frappe.throw(_("Validation failed. Please check the Validation Log for details."))
	
	def validate_import_item(self, item, idx):
		"""Validate a single import item"""
		errors = []
		
		# Validate email format
		if item.customer_email and not frappe.utils.validate_email_address(item.customer_email):
			errors.append(f"Row {idx}: Invalid email format: {item.customer_email}")
		
		# Validate tradeline exists
		if item.tradeline_id and not frappe.db.exists("Tradeline", item.tradeline_id):
			errors.append(f"Row {idx}: Tradeline '{item.tradeline_id}' does not exist")
		
		# Validate quantity
		if item.quantity and item.quantity <= 0:
			errors.append(f"Row {idx}: Quantity must be greater than 0")
		
		# Validate unit price
		if item.unit_price and item.unit_price < 0:
			errors.append(f"Row {idx}: Unit Price cannot be negative")
		
		# Validate discount
		if item.discount_type == "Percentage" and item.discount_value:
			if item.discount_value < 0 or item.discount_value > 100:
				errors.append(f"Row {idx}: Percentage discount must be between 0 and 100")
		
		if item.discount_type == "Amount" and item.discount_value:
			subtotal = (item.quantity or 0) * (item.unit_price or 0)
			if item.discount_value < 0 or item.discount_value > subtotal:
				errors.append(f"Row {idx}: Discount amount cannot exceed subtotal")
		
		# Validate dates
		if item.cart_created_date and item.payment_approved_date:
			if item.cart_created_date > item.payment_approved_date:
				errors.append(f"Row {idx}: Cart Created Date cannot be after Payment Approved Date")
		
		if item.payment_approved_date and item.au_added_date:
			if item.payment_approved_date > item.au_added_date:
				errors.append(f"Row {idx}: Payment Approved Date cannot be after AU Added Date")
		
		return errors
	
	def on_cancel(self):
		"""Delete all associated created documents when import is cancelled"""
		frappe.msgprint("Deleting all associated documents created by this import...")
		
		# Collect all created document IDs
		client_tradelines = []
		payment_requests = []
		carts = []
		customers_to_delete = []
		users_to_delete = []
		
		for item in self.import_items:
			# Always collect tradelines, payments, and carts for deletion
			if item.created_tradeline_id:
				client_tradelines.append(item.created_tradeline_id)
			if item.created_payment_id and item.created_payment_id not in payment_requests:
				payment_requests.append(item.created_payment_id)
			if item.created_cart_id and item.created_cart_id not in carts:
				carts.append(item.created_cart_id)
			
			# Only collect customers and users for deletion if customer_exists is NOT checked
			if not item.customer_exists:
				if item.created_customer_id and item.created_customer_id not in customers_to_delete:
					customers_to_delete.append(item.created_customer_id)
				if item.created_user_id and item.created_user_id not in users_to_delete:
					users_to_delete.append(item.created_user_id)
		
		# Delete in reverse order of creation
		# 1. Delete Client Tradelines
		for ct_id in client_tradelines:
			try:
				if frappe.db.exists("Client Tradelines", ct_id):
					frappe.delete_doc("Client Tradelines", ct_id, force=1, ignore_permissions=True)
					frappe.logger().info(f"Deleted Client Tradeline: {ct_id}")
			except Exception as e:
				frappe.log_error(f"Error deleting Client Tradeline {ct_id}: {str(e)}", "Import Cancellation Error")
		
		# 2. Delete Payment Requests
		for pr_id in payment_requests:
			try:
				if frappe.db.exists("Payment Request", pr_id):
					frappe.delete_doc("Payment Request", pr_id, force=1, ignore_permissions=True)
					frappe.logger().info(f"Deleted Payment Request: {pr_id}")
			except Exception as e:
				frappe.log_error(f"Error deleting Payment Request {pr_id}: {str(e)}", "Import Cancellation Error")
		
		# 3. Delete Tradeline Carts
		for cart_id in carts:
			try:
				if frappe.db.exists("Tradeline Cart", cart_id):
					frappe.delete_doc("Tradeline Cart", cart_id, force=1, ignore_permissions=True)
					frappe.logger().info(f"Deleted Tradeline Cart: {cart_id}")
			except Exception as e:
				frappe.log_error(f"Error deleting Tradeline Cart {cart_id}: {str(e)}", "Import Cancellation Error")
		
		# 4. Delete Customers (only if customer_exists was NOT checked)
		for customer_id in customers_to_delete:
			try:
				if frappe.db.exists("Customer", customer_id):
					frappe.delete_doc("Customer", customer_id, force=1, ignore_permissions=True)
					frappe.logger().info(f"Deleted Customer: {customer_id}")
			except Exception as e:
				frappe.log_error(f"Error deleting Customer {customer_id}: {str(e)}", "Import Cancellation Error")
		
		# 5. Delete Users (only if customer_exists was NOT checked)
		for user_id in users_to_delete:
			try:
				if frappe.db.exists("User", user_id):
					frappe.delete_doc("User", user_id, force=1, ignore_permissions=True)
					frappe.logger().info(f"Deleted User: {user_id}")
			except Exception as e:
				frappe.log_error(f"Error deleting User {user_id}: {str(e)}", "Import Cancellation Error")
		
		# Clear created IDs from import items
		for item in self.import_items:
			item.created_tradeline_id = None
			item.created_payment_id = None
			item.created_cart_id = None
			item.created_customer_id = None
			item.created_user_id = None
			item.import_status = "Cancelled"
			item.db_update()
		
		# Update import status
		self.import_status = "Cancelled"
		self.successful_imports = 0
		
		frappe.db.commit()
		frappe.msgprint("All associated documents have been deleted successfully.", indicator="green")
	
	def on_submit(self):
		"""Process all import items and create records"""
		start_time = time.time()
		
		self.import_status = "Processing"
		self.db_set("import_status", "Processing", update_modified=False)
		
		processing_logs = []
		processing_logs.append(f"=== Import Processing Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
		
		# Group items by customer (either email or existing_customer link) to share cart and payment request
		customer_groups = {}
		for item in self.import_items:
			# Use existing_customer ID if manually selected, otherwise use email
			if item.customer_exists and item.existing_customer:
				group_key = f"existing:{item.existing_customer}"
			else:
				group_key = f"email:{item.customer_email}"
			
			if group_key not in customer_groups:
				customer_groups[group_key] = []
			customer_groups[group_key].append(item)
		
		processing_logs.append(f"Found {len(customer_groups)} unique customers")
		processing_logs.append(f"Processing {len(self.import_items)} total items\n")
		
		# Process each customer group
		for group_key, items in customer_groups.items():
			# Extract display name for logs
			if group_key.startswith("existing:"):
				display_name = group_key.replace("existing:", "Customer: ")
			else:
				display_name = group_key.replace("email:", "")
			
			processing_logs.append(f"\n=== Processing {display_name} ({len(items)} items) ===")
			self.process_customer_group(items, processing_logs)
		
		# Calculate processing time
		end_time = time.time()
		processing_time = end_time - start_time
		self.processing_time = f"{processing_time:.2f} seconds"
		
		# All items must succeed - set status to Completed
		self.import_status = "Completed"
		
		processing_logs.append(f"\n=== Import Processing Completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
		processing_logs.append(f"Total Records: {self.total_records}")
		processing_logs.append(f"Successful: {self.successful_imports}")
		processing_logs.append(f"Failed: {self.failed_imports}")
		processing_logs.append(f"Processing Time: {self.processing_time}")
		
		self.processing_log = "\n".join(processing_logs)
		
		# Save all changes including child table items
		self.db_update()
		
		# Explicitly save child table items to ensure created IDs are persisted
		for item in self.import_items:
			item.db_update()
		
		frappe.db.commit()
	
	def process_customer_group(self, items, logs):
		"""
		Process all import items for a single customer.
		Creates ONE cart and ONE payment request shared by all items.
		
		Flow:
		1. Create/Get User (once per customer)
		2. Create/Get Customer (once per customer, update validation fields if exists)
		3. Create Tradeline Cart with Cart Items (once per customer, is_external=1)
		4. Create Payment Request (once per customer, is_external=1)
		5. Create Client Tradelines (one per item, is_external=1)
		"""
		
		# Use first item for customer details
		first_item = items[0]
		
		# Determine customer identifier for logging
		if first_item.customer_exists and first_item.existing_customer:
			customer_identifier = f"Customer {first_item.existing_customer}"
		else:
			customer_identifier = first_item.customer_email
		
		# Step 1: Create or Get User
		logs.append(f"Step 1: Creating/Getting User for {customer_identifier}")
		user = self.create_or_get_user(first_item, logs)
		logs.append(f"✓ User: {user.name}")
		
		# Step 2: Create or Get Customer
		logs.append(f"Step 2: Creating/Getting Customer")
		customer = self.create_or_get_customer(first_item, user, logs)
		logs.append(f"✓ Customer: {customer.name}")
		
		# Step 3: Create Tradeline Cart with all items
		logs.append(f"Step 3: Creating Tradeline Cart with {len(items)} items")
		cart = self.create_cart_with_items(items, customer, logs)
		logs.append(f"✓ Cart: {cart.name} with total: {cart.total_amount}")
		
		# Step 4: Create Payment Request
		logs.append(f"Step 4: Creating Payment Request")
		payment = self.create_payment_request(first_item, cart, logs)
		logs.append(f"✓ Payment Request: {payment.name}")
		
		# Step 5: Create Client Tradelines (ONE per import item)
		logs.append(f"Step 5: Creating {len(items)} Client Tradelines")
		for idx, item in enumerate(items, start=1):
			client_tradeline = self.create_client_tradeline(item, customer, cart, payment, logs)
			
			# Update item with created record IDs
			item.created_user_id = user.name
			item.created_customer_id = customer.name
			item.created_cart_id = cart.name
			item.created_payment_id = payment.name
			item.created_tradeline_id = client_tradeline.name
			item.import_status = "Success"
			self.successful_imports += 1
			
			logs.append(f"  ✓ Item {idx}/{len(items)}: Client Tradeline {client_tradeline.name}")
	
	def create_or_get_user(self, item, logs):
		"""
		Create a new User or get existing User.
		If existing_customer is selected, get user from customer's email.
		
		This explicitly handles User creation which is required before Customer creation.
		"""
		# If existing customer is selected, get email from customer record
		if item.customer_exists and item.existing_customer:
			customer = frappe.get_doc("Customer", item.existing_customer)
			user_email = customer.email_id
			if not user_email:
				# Fallback to represents_company if email_id is not set
				user_email = customer.represents_company if customer.represents_company else item.customer_email
			logs.append(f"  → Using email from existing customer: {user_email}")
		else:
			user_email = item.customer_email
		
		# Check if user exists
		if frappe.db.exists("User", user_email):
			logs.append(f"  → User already exists: {user_email}")
			return frappe.get_doc("User", user_email)
		
		# Create new user
		logs.append(f"  → Creating new User: {user_email}")
		
		user = frappe.get_doc({
			"doctype": "User",
			"email": user_email,
			"first_name": item.customer_name or user_email.split("@")[0],
			"enabled": 1,
			"send_welcome_email": 0,  # Don't send welcome email for imports
			"user_type": "Website User"
		})
		
		# Set password if provided, otherwise auto-generate
		if item.user_password:
			user.new_password = item.user_password
			logs.append(f"  → Using provided password")
		else:
			# Frappe will auto-generate password
			logs.append(f"  → Auto-generating password")
		
		# Set role profile if provided
		if item.role_profile:
			user.role_profile_name = item.role_profile
			logs.append(f"  → Assigning role profile: {item.role_profile}")
		
		# Set date of birth if provided
		if item.customer_dob:
			user.birth_date = item.customer_dob
			logs.append(f"  → Setting date of birth: {item.customer_dob}")
		
		user.insert(ignore_permissions=True)
		
		# Set creation time to when cart was created (earliest date)
		if item.cart_created_date:
			frappe.db.sql("""
				UPDATE `tabUser`
				SET creation = %s, modified = %s
				WHERE name = %s
			""", (item.cart_created_date, item.cart_created_date, user.name))
			logs.append(f"  → User creation time set to: {item.cart_created_date}")
		
		logs.append(f"  → User created successfully: {user.name}")
		
		return user
	
	def create_or_get_customer(self, item, user, logs):
		"""
		Create new Customer or get existing Customer.
		If customer exists, update validation fields if they're not already set.
		Supports manual selection via existing_customer link field.
		"""
		
		# Priority 1: Check if user manually selected an existing customer
		if item.customer_exists and item.existing_customer:
			logs.append(f"  → Using manually selected customer: {item.existing_customer}")
			customer = frappe.get_doc("Customer", item.existing_customer)
			
			# Update validation fields if not already set
			updated_fields = []
			
			if not customer.get("has_signed_agreement"):
				customer.has_signed_agreement = item.has_signed_agreement if item.has_signed_agreement is not None else 1
				updated_fields.append("has_signed_agreement")
			
			if not customer.get("is_questionnaire_filled"):
				customer.is_questionnaire_filled = item.is_questionnaire_filled if item.is_questionnaire_filled is not None else 1
				updated_fields.append("is_questionnaire_filled")
			
			if not customer.get("agreement_signed_date"):
				customer.agreement_signed_date = item.agreement_signed_date or item.cart_created_date
				updated_fields.append("agreement_signed_date")
			
			if not customer.get("questionnaire_filled_date"):
				customer.questionnaire_filled_date = item.questionnaire_filled_date or item.cart_created_date
				updated_fields.append("questionnaire_filled_date")
			
			# Save if any fields were updated
			if updated_fields:
				customer.save(ignore_permissions=True)
				logs.append(f"  → Updated customer fields: {', '.join(updated_fields)}")
			else:
				logs.append(f"  → Customer already has all required fields set")
			
			logs.append(f"  → Using selected customer (has_signed_agreement={customer.has_signed_agreement}, is_questionnaire_filled={customer.is_questionnaire_filled})")
			return customer
		
		# Priority 2: Check if customer exists by email (auto-detection)
		existing_customer = frappe.db.get_value(
			"Customer",
			{"email_id": item.customer_email},
			["name", "has_signed_agreement", "is_questionnaire_filled"],
			as_dict=True
		)
		
		if existing_customer:
			logs.append(f"  → Customer already exists: {existing_customer.name}")
			customer = frappe.get_doc("Customer", existing_customer.name)
			
			# Update validation fields if not already set (don't override existing values)
			updated_fields = []
			
			if not customer.get("has_signed_agreement"):
				customer.has_signed_agreement = item.has_signed_agreement if item.has_signed_agreement is not None else 1
				updated_fields.append("has_signed_agreement")
			
			if not customer.get("is_questionnaire_filled"):
				customer.is_questionnaire_filled = item.is_questionnaire_filled if item.is_questionnaire_filled is not None else 1
				updated_fields.append("is_questionnaire_filled")
			
			if not customer.get("agreement_signed_date"):
				customer.agreement_signed_date = item.agreement_signed_date or item.cart_created_date
				updated_fields.append("agreement_signed_date")
			
			if not customer.get("questionnaire_filled_date"):
				customer.questionnaire_filled_date = item.questionnaire_filled_date or item.cart_created_date
				updated_fields.append("questionnaire_filled_date")
			
			# Update phone if not set
			if not customer.mobile_no and item.customer_phone:
				customer.mobile_no = item.customer_phone
				updated_fields.append("mobile_no")
			
			# Save if any fields were updated
			if updated_fields:
				customer.save(ignore_permissions=True)
				logs.append(f"  → Updated customer fields: {', '.join(updated_fields)}")
			else:
				logs.append(f"  → Customer already has all required fields set")
			
			logs.append(f"  → Using existing customer (has_signed_agreement={customer.has_signed_agreement}, is_questionnaire_filled={customer.is_questionnaire_filled})")
			return customer
		
		# Create new customer
		logs.append(f"  → Creating new Customer for user: {user.name}")
		
		customer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": item.customer_name,
			"customer_type": "Individual",
			"customer_group": "Individual",
			"territory": "All Territories",
			"email_id": item.customer_email,
			"mobile_no": item.customer_phone,
			"is_external": 1 if self.suppress_emails else 0,
			"account_manager": item.account_manager if item.account_manager else None,
			# "represents_company": user.name,  # Link to User
			# Set validation fields for checkout (default to True for historical imports)
			"has_signed_agreement": item.has_signed_agreement if item.has_signed_agreement is not None else 1,
			"is_questionnaire_filled": item.is_questionnaire_filled if item.is_questionnaire_filled is not None else 1,
			"agreement_signed_date": item.agreement_signed_date or item.cart_created_date,
			"questionnaire_filled_date": item.questionnaire_filled_date or item.cart_created_date,
		})
		
		customer.insert(ignore_permissions=True)
		
		# Set creation time to when cart was created
		if item.cart_created_date:
			frappe.db.sql("""
				UPDATE `tabCustomer`
				SET creation = %s, modified = %s
				WHERE name = %s
			""", (item.cart_created_date, item.cart_created_date, customer.name))
			logs.append(f"  → Customer creation time set to: {item.cart_created_date}")
		
		logs.append(f"  → Customer created: {customer.name} (is_external={customer.is_external}, has_signed_agreement={customer.has_signed_agreement}, is_questionnaire_filled={customer.is_questionnaire_filled})")
		
		# Create address if address fields are provided
		if item.address_line1 or item.city or item.state or item.pincode:
			self.create_customer_address(customer, item, logs)
		
		return customer
	
	def create_cart_with_items(self, items, customer, logs):
		"""Create Tradeline Cart record with multiple items and is_external flag"""
		logs.append(f"  → Creating Cart for customer: {customer.name}")
		
		# Get user_id from customer's email (represents_company might be NULL for existing customers)
		user_id = customer.represents_company
		if not user_id:
			# If represents_company is not set, find user by customer's email
			if customer.email_id:
				user_id = customer.email_id
				logs.append(f"  → Using customer email as user_id: {user_id}")
			else:
				frappe.throw(_(f"Customer {customer.name} has no email_id or represents_company field set"))
		
		# Use the earliest cart created date from all items
		cart_created_date = min([item.cart_created_date for item in items if item.cart_created_date])
		
		# Calculate total amounts across all items
		total_subtotal = 0
		total_discount_amount = 0
		
		cart_items = []
		for item in items:
			item_subtotal = item.quantity * item.unit_price
			item_discount_amount = 0
			
			if item.discount_type == "Percentage" and item.discount_value:
				item_discount_amount = item_subtotal * (item.discount_value / 100)
			elif item.discount_type == "Amount" and item.discount_value:
				item_discount_amount = item.discount_value
			
			total_subtotal += item_subtotal
			total_discount_amount += item_discount_amount
			
			# Add cart item with correct field names for Tradeline Cart Item
			cart_items.append({
				"tradeline": item.tradeline_id,  # Field name is 'tradeline', not 'tradeline_id'
				"quantity": item.quantity,
				"rate": item.unit_price,  # Field name is 'rate', not 'unit_price'
				"amount": item_subtotal - item_discount_amount  # Field name is 'amount'
			})
			
			logs.append(f"  → Item: {item.tradeline_id} x {item.quantity} = ${item_subtotal:.2f}")
		
		total_amount = total_subtotal - total_discount_amount
		
		# Create Tradeline Cart
		cart = frappe.get_doc({
			"doctype": "Tradeline Cart",
			"user_id": user_id,  # Link to User (email or represents_company)
			"customer": customer.name,
			"status": "Completed",
			"subtotal": total_subtotal,
			"discount_amount": total_discount_amount,
			"total_amount": total_amount,
			"is_external": 1 if self.suppress_emails else 0
		})
		
		# Add cart items
		for cart_item in cart_items:
			cart.append("items", cart_item)
		
		cart.insert(ignore_permissions=True)
		
		# Set creation time to cart_created_date from import
		if cart_created_date:
			frappe.db.sql("""
				UPDATE `tabTradeline Cart`
				SET creation = %s, modified = %s
				WHERE name = %s
			""", (cart_created_date, cart_created_date, cart.name))
			logs.append(f"  → Cart creation time set to: {cart_created_date}")
		
		logs.append(f"  → Cart created: {cart.name} (subtotal={total_subtotal}, discount={total_discount_amount}, total={total_amount}, is_external={cart.is_external})")
		
		return cart
	
	def create_payment_request(self, item, cart, logs):
		"""Create Payment Request record with is_external flag"""
		logs.append(f"  → Creating Payment Request for cart: {cart.name}")
		
		# Generate unique title for payment request
		payment_title = f"PAY-{cart.name}-{frappe.utils.now_datetime().strftime('%Y%m%d%H%M%S')}"
		
		# Get payment method - use first available or create a default
		payment_method = frappe.db.get_value("Payment Configuration", {"is_active": 1, "name": "Zelle"}, "name")
		if not payment_method:
			payment_method = frappe.db.get_value("Payment Configuration", {}, "name")
		
		if not payment_method:
			frappe.throw(_("No Payment Configuration found. Please create at least one Payment Configuration."))
		
		payment = frappe.get_doc({
			"doctype": "Payment Request",
			"title": payment_title,
			"cart_id": cart.name,
			"customer": cart.customer,  # Field is 'customer', not 'customer_id'
			"amount": cart.total_amount,
			"total_amount": cart.total_amount,
			"payment_method": payment_method,
			"status": item.payment_status,  # Field is 'status', not 'payment_status'
			"approval_status": item.approval_status,
			"proof_of_payment": item.proof_of_payment_url,
			"is_external": 1 if self.suppress_emails else 0,
			"is_manual_payment": 1,  # Mark as manual payment for imported records
			"approved_at": item.payment_approved_date,  # Field is 'approved_at'
			"completed_at": item.payment_approved_date if item.payment_status == "Completed" else None
		})
		
		payment.insert(ignore_permissions=True)
		
		# Set creation time to payment_approved_date from import
		if item.payment_approved_date:
			frappe.db.sql("""
				UPDATE `tabPayment Request`
				SET creation = %s, modified = %s
				WHERE name = %s
			""", (item.payment_approved_date, item.payment_approved_date, payment.name))
			logs.append(f"  → Payment Request creation time set to: {item.payment_approved_date}")
		
		# Handle file attachment for proof of payment - attach to Customer, not Payment Request
		if item.proof_of_payment_url:
			customer_doc = frappe.get_doc("Customer", cart.customer)
			self.handle_file_attachment(
				item.proof_of_payment_url, 
				"Customer", 
				customer_doc.name, 
				"proof_of_payment", 
				logs,
				customer_name=customer_doc.customer_name
			)
		
		logs.append(f"  → Payment Request created: {payment.name} (is_external={payment.is_external})")
		
		return payment
	
	def create_client_tradeline(self, item, customer, cart, payment, logs):
		"""
		Create ONE Client Tradeline record with is_external flag.
		
		Each import item creates exactly ONE Client Tradeline.
		"""
		# Calculate individual item amounts
		item_subtotal = item.quantity * item.unit_price
		item_discount_amount = 0
		
		if item.discount_type == "Percentage" and item.discount_value:
			item_discount_amount = item_subtotal * (item.discount_value / 100)
		elif item.discount_type == "Amount" and item.discount_value:
			item_discount_amount = item.discount_value
		
		item_total_amount = item_subtotal - item_discount_amount
		
		client_tradeline = frappe.get_doc({
			"doctype": "Client Tradelines",
			"customer": customer.name,
			"tradeline": item.tradeline_id,
			"cart": cart.name,
			"payment_request": payment.name,
			"quantity": item.quantity,
			"unit_price": item.unit_price,
			"subtotal": item_subtotal,
			"discount_type": item.discount_type if item.discount_type else None,
			"discount_value": item.discount_value if item.discount_value else None,
			"discount_amount": item_discount_amount,
			"total_amount": item_total_amount,
			"status": item.client_tradeline_status,
			"au_added_date": item.au_added_date,
			"expiry_date": item.expiry_date,
			"proof_of_au": item.proof_of_au_url,
			"is_external": 1 if self.suppress_emails else 0
		})
		
		client_tradeline.insert(ignore_permissions=True)
		
		# Set creation time to payment_approved_date (same as Payment Request)
		# This ensures Client Tradeline creation time matches when payment was approved
		if item.payment_approved_date:
			frappe.db.sql("""
				UPDATE `tabClient Tradelines`
				SET creation = %s, modified = %s, status = %s, expiry_date = %s
				WHERE name = %s
			""", (item.payment_approved_date, item.payment_approved_date, item.client_tradeline_status, item.expiry_date, client_tradeline.name))
			logs.append(f"  → Client Tradeline creation time set to: {item.payment_approved_date}")
		
		# Ensure status and expiry_date are preserved after insert
		frappe.db.set_value("Client Tradelines", client_tradeline.name, {
			"status": item.client_tradeline_status,
			"expiry_date": item.expiry_date
		}, update_modified=False)
		
		# Handle file attachment for proof of AU - attach to Customer, not Client Tradelines
		if item.proof_of_au_url:
			self.handle_file_attachment(
				item.proof_of_au_url, 
				"Customer", 
				customer.name, 
				"proof_of_au", 
				logs,
				customer_name=customer.customer_name
			)
		
		return client_tradeline
	
	def create_customer_address(self, customer, item, logs):
		"""
		Create address for customer using the same approach as broker_create_client in auth.py
		"""
		try:
			logs.append(f"  → Creating address for customer: {customer.name}")
			
			# Prepare address data
			address = frappe.get_doc({
				"doctype": "Address",
				"address_type": "Billing",
				"address_title": f"{customer.customer_name} - Primary",
				"address_line1": item.address_line1,
				"address_line2": item.address_line2,
				"city": item.city,
				"state": item.state,
				"pincode": item.pincode,
				"country": item.country or "United States",
				"email_id": item.customer_email,
				"phone": item.customer_phone,
				"is_primary_address": 1,
				"is_shipping_address": 1,
				"links": [{
					"link_doctype": "Customer",
					"link_name": customer.name
				}]
			})
			
			address.insert(ignore_permissions=True)
			
			# Update customer's primary address link
			customer.customer_primary_address = address.name
			customer.primary_address = address.address_line1
			customer.save(ignore_permissions=True)
			
			logs.append(f"  → Address created: {address.name}")
			
		except Exception as e:
			logs.append(f"  → Warning: Could not create address: {str(e)}")
			# Continue processing even if address creation fails
			pass
	
	def handle_file_attachment(self, file_url, target_doctype, target_docname, field_name, logs, customer_name=None):
		"""
		Handle file attachment by ensuring proper naming convention and folder organization.
		
		Conforms to files.py upload strategy:
		- Naming: Customer_{customer_name}_{field_name} (matching broker_create_client pattern)
		- Folder organization: Home/{file_type} for private files
		- Uses create_or_get_folder() function from files.py
		- Files are attached to Customer doctype, not to other doctypes
		"""
		if not file_url:
			return
		
		try:
			# Import the create_or_get_folder function from files.py
			from rockettradeline.rockettradeline.api.files import create_or_get_folder
			from werkzeug.utils import secure_filename
			
			# Get the file document
			file_doc = frappe.get_doc("File", {"file_url": file_url})
			
			# Determine the file type based on field_name (proof_of_payment, proof_of_au, etc.)
			file_type = field_name  # This will be "proof_of_payment" or "proof_of_au"
			
			# Get the original filename and extract extension
			original_filename = file_doc.file_name
			file_ext = frappe.utils.get_file_extension(original_filename)
			
			# Create base filename using the file_type (with extension)
			base_filename = f"{file_type}.{file_ext}" if file_ext else file_type
			base_filename = secure_filename(base_filename)
			
			# Create custom filename: Customer_{customer_name}_{field_name}
			# This matches the pattern used in broker_create_client
			if customer_name:
				clean_customer_name = "".join(c for c in customer_name if c.isalnum() or c in (' ', '-', '_')).replace(' ', '_')
				custom_filename = f"Customer_{clean_customer_name}_{base_filename}"
			else:
				custom_filename = f"Customer_{target_docname}_{base_filename}"
			
			custom_filename = secure_filename(custom_filename)
			
			# Create or get folder for this file type (e.g., Home/proof_of_payment)
			folder_path = create_or_get_folder(file_type, "Home")
			
			# Update the file document with new name, folder, and attachment details
			file_doc.file_name = custom_filename
			file_doc.folder = folder_path
			file_doc.is_private = 1  # Ensure files are private
			file_doc.attached_to_doctype = target_doctype
			file_doc.attached_to_name = target_docname
			file_doc.save(ignore_permissions=True)
			
			# Update the target record with the new file URL
			target_doc = frappe.get_doc(target_doctype, target_docname)
			target_doc.set(field_name, file_doc.file_url)
			target_doc.save(ignore_permissions=True)
			
			logs.append(f"  → File attached: {custom_filename} → {target_doctype} {target_docname} (folder: {folder_path})")
			
		except Exception as e:
			logs.append(f"  → Warning: Could not process file attachment {file_url}: {str(e)}")
			# Continue processing even if file handling fails
			pass

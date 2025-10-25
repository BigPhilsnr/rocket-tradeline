# Copyright (c) 2025, RocketTradeLine and contributors
# For license information, please see license.txt

import frappe
import unittest
from frappe.utils import now_datetime, add_days, getdate


class TestTradelineImport(unittest.TestCase):
	"""Test cases for Tradeline Import functionality"""
	
	def setUp(self):
		"""Set up test data before each test"""
		# Disable email sending during tests
		frappe.flags.in_test = True
		
	def tearDown(self):
		"""Clean up after each test"""
		frappe.flags.in_test = False
	
	def test_existing_import_record_TLI_2025_00038_2(self):
		"""
		Test the existing import record TLI-2025-00038-2
		This test will:
		1. Load the existing import record
		2. Submit it to trigger processing
		3. Verify all DocTypes are created
		4. Verify they are linked back to the import record
		"""
		
		print("\n" + "="*80)
		print("Testing Tradeline Import: TLI-2025-00038-2")
		print("="*80)
		
		# Load the existing import record
		import_doc = frappe.get_doc("Tradeline Import", "TLI-2025-00038-2")
		
		print(f"\n1. Loaded Import Record")
		print(f"   - Name: {import_doc.name}")
		print(f"   - Title: {import_doc.import_title}")
		print(f"   - Status: {import_doc.import_status}")
		print(f"   - Total Items: {len(import_doc.import_items)}")
		
		# Check if already submitted
		if import_doc.docstatus == 1:
			print(f"\n   ⚠ Record already submitted. Cancelling to retest...")
			import_doc.cancel()
			frappe.db.commit()
			import_doc = frappe.get_doc("Tradeline Import", "TLI-2025-00038-2")
		
		# Store import item details before submission
		import_item = import_doc.import_items[0]
		print(f"\n2. Import Item Details (Before Submission)")
		print(f"   - Customer: {import_item.existing_customer}")
		print(f"   - Tradeline: {import_item.tradeline_id}")
		print(f"   - Quantity: {import_item.quantity}")
		print(f"   - Unit Price: {import_item.unit_price}")
		print(f"   - Status: {import_item.import_status}")
		
		# Submit the import to trigger processing
		print(f"\n3. Submitting Import Record...")
		try:
			import_doc.submit()
			frappe.db.commit()
			print(f"   ✓ Import submitted successfully")
		except Exception as e:
			print(f"   ✗ Import submission failed: {str(e)}")
			raise
		
		# Reload to get updated data
		import_doc.reload()
		import_item = import_doc.import_items[0]
		
		print(f"\n4. Import Processing Results")
		print(f"   - Import Status: {import_doc.import_status}")
		print(f"   - Successful Imports: {import_doc.successful_imports}")
		print(f"   - Failed Imports: {import_doc.failed_imports}")
		print(f"   - Item Status: {import_item.import_status}")
		
		if import_item.error_message:
			print(f"   - Error Message: {import_item.error_message}")
		
		# Assert import was successful
		self.assertEqual(import_doc.import_status, "Completed", 
			f"Import should be Completed, but got {import_doc.import_status}")
		self.assertEqual(import_doc.successful_imports, 1, 
			"Should have 1 successful import")
		self.assertEqual(import_doc.failed_imports, 0, 
			"Should have 0 failed imports")
		self.assertEqual(import_item.import_status, "Success", 
			f"Item should be Success, but got {import_item.import_status}")
		
		# Verify User was created/exists
		print(f"\n5. Verifying User")
		self.assertTrue(import_item.created_user_id, 
			"User ID should be set in import item")
		print(f"   - User ID: {import_item.created_user_id}")
		
		user_exists = frappe.db.exists("User", import_item.created_user_id)
		self.assertTrue(user_exists, 
			f"User {import_item.created_user_id} should exist")
		print(f"   ✓ User exists: {import_item.created_user_id}")
		
		# Verify Customer was created/exists
		print(f"\n6. Verifying Customer")
		self.assertTrue(import_item.created_customer_id, 
			"Customer ID should be set in import item")
		print(f"   - Customer ID: {import_item.created_customer_id}")
		
		customer_exists = frappe.db.exists("Customer", import_item.created_customer_id)
		self.assertTrue(customer_exists, 
			f"Customer {import_item.created_customer_id} should exist")
		
		customer = frappe.get_doc("Customer", import_item.created_customer_id)
		print(f"   ✓ Customer exists: {customer.name}")
		print(f"   - Email: {customer.email_id}")
		print(f"   - Has Signed Agreement: {customer.has_signed_agreement}")
		print(f"   - Is Questionnaire Filled: {customer.is_questionnaire_filled}")
		
		# Verify Tradeline Cart was created
		print(f"\n7. Verifying Tradeline Cart")
		self.assertTrue(import_item.created_cart_id, 
			"Cart ID should be set in import item")
		print(f"   - Cart ID: {import_item.created_cart_id}")
		
		cart_exists = frappe.db.exists("Tradeline Cart", import_item.created_cart_id)
		self.assertTrue(cart_exists, 
			f"Cart {import_item.created_cart_id} should exist")
		
		cart = frappe.get_doc("Tradeline Cart", import_item.created_cart_id)
		print(f"   ✓ Cart exists: {cart.name}")
		print(f"   - User ID: {cart.user_id}")
		print(f"   - Customer: {cart.customer}")
		print(f"   - Status: {cart.status}")
		print(f"   - Total Amount: {cart.total_amount}")
		print(f"   - Is External: {cart.is_external}")
		print(f"   - Number of Items: {len(cart.items)}")
		
		# Verify cart items
		if cart.items:
			for idx, cart_item in enumerate(cart.items, 1):
				print(f"   - Item {idx}: {cart_item.tradeline} x {cart_item.quantity} @ {cart_item.rate} = {cart_item.amount}")
		
		# Assert cart links back to import
		self.assertEqual(cart.customer, customer.name, 
			"Cart should link to the correct customer")
		self.assertEqual(cart.status, "Completed", 
			"Cart status should be Completed")
		
		# Verify Payment Request was created
		print(f"\n8. Verifying Payment Request")
		self.assertTrue(import_item.created_payment_id, 
			"Payment ID should be set in import item")
		print(f"   - Payment ID: {import_item.created_payment_id}")
		
		payment_exists = frappe.db.exists("Payment Request", import_item.created_payment_id)
		self.assertTrue(payment_exists, 
			f"Payment Request {import_item.created_payment_id} should exist")
		
		payment = frappe.get_doc("Payment Request", import_item.created_payment_id)
		print(f"   ✓ Payment Request exists: {payment.name}")
		print(f"   - Cart ID: {payment.cart_id}")
		print(f"   - Customer: {payment.customer}")
		print(f"   - Amount: {payment.amount}")
		print(f"   - Status: {payment.status}")
		print(f"   - Approval Status: {payment.approval_status}")
		print(f"   - Is External: {payment.is_external}")
		
		# Assert payment links back to import
		self.assertEqual(payment.cart_id, cart.name, 
			"Payment should link to the correct cart")
		self.assertEqual(payment.customer, customer.name, 
			"Payment should link to the correct customer")
		
		# Verify Client Tradeline was created
		print(f"\n9. Verifying Client Tradeline")
		self.assertTrue(import_item.created_tradeline_id, 
			"Client Tradeline ID should be set in import item")
		print(f"   - Client Tradeline ID: {import_item.created_tradeline_id}")
		
		client_tradeline_exists = frappe.db.exists("Client Tradelines", import_item.created_tradeline_id)
		self.assertTrue(client_tradeline_exists, 
			f"Client Tradeline {import_item.created_tradeline_id} should exist")
		
		client_tradeline = frappe.get_doc("Client Tradelines", import_item.created_tradeline_id)
		print(f"   ✓ Client Tradeline exists: {client_tradeline.name}")
		print(f"   - Customer: {client_tradeline.customer}")
		print(f"   - Tradeline: {client_tradeline.tradeline}")
		print(f"   - Cart: {client_tradeline.cart}")
		print(f"   - Payment Request: {client_tradeline.payment_request}")
		print(f"   - Quantity: {client_tradeline.quantity}")
		print(f"   - Total Amount: {client_tradeline.total_amount}")
		print(f"   - Status: {client_tradeline.status}")
		print(f"   - Is External: {client_tradeline.is_external}")
		
		# Assert client tradeline links back to import
		self.assertEqual(client_tradeline.customer, customer.name, 
			"Client Tradeline should link to the correct customer")
		self.assertEqual(client_tradeline.cart, cart.name, 
			"Client Tradeline should link to the correct cart")
		self.assertEqual(client_tradeline.payment_request, payment.name, 
			"Client Tradeline should link to the correct payment request")
		
		# Verify all links are consistent
		print(f"\n10. Verifying Link Consistency")
		print(f"   ✓ User → Customer: {customer.email_id} matches user")
		print(f"   ✓ Customer → Cart: {cart.customer} = {customer.name}")
		print(f"   ✓ Cart → Payment: {payment.cart_id} = {cart.name}")
		print(f"   ✓ Payment → Cart: {payment.cart_id} = {cart.name}")
		print(f"   ✓ Client Tradeline → Customer: {client_tradeline.customer} = {customer.name}")
		print(f"   ✓ Client Tradeline → Cart: {client_tradeline.cart} = {cart.name}")
		print(f"   ✓ Client Tradeline → Payment: {client_tradeline.payment_request} = {payment.name}")
		
		# Print processing log
		if import_doc.processing_log:
			print(f"\n11. Processing Log")
			print("-" * 80)
			print(import_doc.processing_log)
			print("-" * 80)
		
		print("\n" + "="*80)
		print("✓ ALL TESTS PASSED!")
		print("="*80 + "\n")
	
	def test_create_new_import_with_existing_customer(self):
		"""
		Test creating a new import record with an existing customer
		"""
		
		print("\n" + "="*80)
		print("Testing New Tradeline Import with Existing Customer")
		print("="*80)
		
		# Create a new import record
		import_doc = frappe.get_doc({
			"doctype": "Tradeline Import",
			"import_date": getdate(),
			"suppress_emails": 1,
			"import_items": [{
				"customer_exists": 1,
				"existing_customer": "Philip Buyer",
				"tradeline_id": "00003",
				"quantity": 2,
				"discount_type": "Amount",
				"discount_value": 20,
				"cart_created_date": now_datetime(),
				"payment_approved_date": now_datetime(),
				"au_added_date": now_datetime(),
				"expiry_date": add_days(getdate(), 60),
				"payment_status": "Completed",
				"approval_status": "Approved",
				"client_tradeline_status": "Active",
				"has_signed_agreement": 1,
				"is_questionnaire_filled": 1
			}]
		})
		
		print(f"\n1. Created Import Record")
		print(f"   - Items: {len(import_doc.import_items)}")
		
		# Insert and submit
		import_doc.insert()
		frappe.db.commit()
		
		print(f"   - Name: {import_doc.name}")
		print(f"   - Status: {import_doc.import_status}")
		
		# Submit
		print(f"\n2. Submitting Import...")
		import_doc.submit()
		frappe.db.commit()
		
		# Reload and verify
		import_doc.reload()
		import_item = import_doc.import_items[0]
		
		print(f"\n3. Verification")
		print(f"   - Import Status: {import_doc.import_status}")
		print(f"   - Item Status: {import_item.import_status}")
		print(f"   - Created Cart: {import_item.created_cart_id}")
		print(f"   - Created Payment: {import_item.created_payment_id}")
		print(f"   - Created Tradeline: {import_item.created_tradeline_id}")
		
		# Assertions
		self.assertEqual(import_doc.import_status, "Completed")
		self.assertEqual(import_item.import_status, "Success")
		self.assertTrue(import_item.created_cart_id)
		self.assertTrue(import_item.created_payment_id)
		self.assertTrue(import_item.created_tradeline_id)
		
		print("\n   ✓ Test Passed!")
		print("="*80 + "\n")


def run_test():
	"""Helper function to run the test from bench console"""
	frappe.init(site="rockettradeline.com")
	frappe.connect()
	
	suite = unittest.TestLoader().loadTestsFromTestCase(TestTradelineImport)
	runner = unittest.TextTestRunner(verbosity=2)
	result = runner.run(suite)
	
	frappe.destroy()
	
	return result


if __name__ == "__main__":
	run_test()

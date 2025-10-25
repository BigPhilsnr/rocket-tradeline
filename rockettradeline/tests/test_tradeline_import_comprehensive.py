# Copyright (c) 2025, RocketTradeLine and contributors
# For license information, please see license.txt

import frappe
import unittest
from frappe.utils import now_datetime, add_days, getdate, add_to_date
from datetime import datetime


class TestTradelineImportComprehensive(unittest.TestCase):
	"""Comprehensive test suite for Tradeline Import functionality"""
	
	@classmethod
	def setUpClass(cls):
		"""Set up test data once for all tests"""
		frappe.flags.in_test = True
		cls.test_data = cls.create_test_data()
		
	@classmethod
	def tearDownClass(cls):
		"""Clean up after all tests"""
		frappe.flags.in_test = False
		cls.cleanup_test_data()
	
	@classmethod
	def create_test_data(cls):
		"""Create necessary test data"""
		data = {
			'tradelines': [],
			'customers': [],
			'users': []
		}
		
		# Ensure test tradeline exists
		if not frappe.db.exists("Tradeline", "00003"):
			print("⚠ Warning: Tradeline 00003 not found, using any available tradeline")
			tradeline = frappe.db.get_value("Tradeline", {}, ["name", "price"], as_dict=True)
			if tradeline:
				data['tradelines'].append(tradeline.name)
		else:
			data['tradelines'].append("00003")
		
		return data
	
	@classmethod
	def cleanup_test_data(cls):
		"""Clean up test data created during tests"""
		# Note: Be careful with cleanup in production
		pass
	
	def setUp(self):
		"""Set up before each test"""
		self.import_records_created = []
	
	def tearDown(self):
		"""Clean up after each test"""
		# Cancel and delete test imports
		for import_name in self.import_records_created:
			try:
				if frappe.db.exists("Tradeline Import", import_name):
					import_doc = frappe.get_doc("Tradeline Import", import_name)
					if import_doc.docstatus == 1:
						import_doc.cancel()
					frappe.delete_doc("Tradeline Import", import_name, force=1)
					frappe.db.commit()
			except Exception as e:
				print(f"Cleanup error for {import_name}: {str(e)}")
	
	def create_import_doc(self, items, suppress_emails=True):
		"""Helper to create an import document"""
		import_doc = frappe.get_doc({
			"doctype": "Tradeline Import",
			"import_date": getdate(),
			"suppress_emails": 1 if suppress_emails else 0,
			"import_items": items
		})
		import_doc.insert()
		frappe.db.commit()
		self.import_records_created.append(import_doc.name)
		return import_doc
	
	def verify_doctype_creation(self, import_item, expected_status="Success"):
		"""
		Verify all doctypes are created and properly linked
		Returns dict with verification results
		"""
		results = {
			'user': {'exists': False, 'id': None, 'verified': False},
			'customer': {'exists': False, 'id': None, 'verified': False},
			'cart': {'exists': False, 'id': None, 'verified': False},
			'payment': {'exists': False, 'id': None, 'verified': False},
			'client_tradeline': {'exists': False, 'id': None, 'verified': False},
			'all_verified': False
		}
		
		# Check import status
		self.assertEqual(import_item.import_status, expected_status,
			f"Import item status should be {expected_status}")
		
		if expected_status != "Success":
			return results
		
		# Verify User
		if import_item.created_user_id:
			results['user']['id'] = import_item.created_user_id
			results['user']['exists'] = frappe.db.exists("User", import_item.created_user_id)
			results['user']['verified'] = results['user']['exists']
			self.assertTrue(results['user']['exists'], 
				f"User {import_item.created_user_id} should exist")
		
		# Verify Customer
		if import_item.created_customer_id:
			results['customer']['id'] = import_item.created_customer_id
			results['customer']['exists'] = frappe.db.exists("Customer", import_item.created_customer_id)
			if results['customer']['exists']:
				customer = frappe.get_doc("Customer", import_item.created_customer_id)
				# Verify validation fields
				self.assertIsNotNone(customer.has_signed_agreement, "has_signed_agreement should be set")
				self.assertIsNotNone(customer.is_questionnaire_filled, "is_questionnaire_filled should be set")
				results['customer']['verified'] = True
			self.assertTrue(results['customer']['verified'], 
				f"Customer {import_item.created_customer_id} verification failed")
		
		# Verify Cart
		if import_item.created_cart_id:
			results['cart']['id'] = import_item.created_cart_id
			results['cart']['exists'] = frappe.db.exists("Tradeline Cart", import_item.created_cart_id)
			if results['cart']['exists']:
				cart = frappe.get_doc("Tradeline Cart", import_item.created_cart_id)
				# Verify links
				self.assertEqual(cart.customer, import_item.created_customer_id,
					"Cart should link to correct customer")
				self.assertEqual(cart.status, "Completed", "Cart status should be Completed")
				self.assertTrue(len(cart.items) > 0, "Cart should have items")
				# Verify timestamp
				if import_item.cart_created_date:
					cart_creation = frappe.db.get_value("Tradeline Cart", cart.name, "creation")
					self.assertEqual(str(cart_creation), str(import_item.cart_created_date),
						f"Cart creation time should match cart_created_date")
				results['cart']['verified'] = True
			self.assertTrue(results['cart']['verified'], 
				f"Cart {import_item.created_cart_id} verification failed")
		
		# Verify Payment Request
		if import_item.created_payment_id:
			results['payment']['id'] = import_item.created_payment_id
			results['payment']['exists'] = frappe.db.exists("Payment Request", import_item.created_payment_id)
			if results['payment']['exists']:
				payment = frappe.get_doc("Payment Request", import_item.created_payment_id)
				# Verify links
				self.assertEqual(payment.cart_id, import_item.created_cart_id,
					"Payment should link to correct cart")
				self.assertEqual(payment.customer, import_item.created_customer_id,
					"Payment should link to correct customer")
				# Verify timestamp
				if import_item.payment_approved_date:
					payment_creation = frappe.db.get_value("Payment Request", payment.name, "creation")
					self.assertEqual(str(payment_creation), str(import_item.payment_approved_date),
						f"Payment creation time should match payment_approved_date")
				results['payment']['verified'] = True
			self.assertTrue(results['payment']['verified'], 
				f"Payment {import_item.created_payment_id} verification failed")
		
		# Verify Client Tradeline
		if import_item.created_tradeline_id:
			results['client_tradeline']['id'] = import_item.created_tradeline_id
			results['client_tradeline']['exists'] = frappe.db.exists("Client Tradelines", import_item.created_tradeline_id)
			if results['client_tradeline']['exists']:
				client_tradeline = frappe.get_doc("Client Tradelines", import_item.created_tradeline_id)
				# Verify links
				self.assertEqual(client_tradeline.customer, import_item.created_customer_id,
					"Client Tradeline should link to correct customer")
				self.assertEqual(client_tradeline.cart, import_item.created_cart_id,
					"Client Tradeline should link to correct cart")
				self.assertEqual(client_tradeline.payment_request, import_item.created_payment_id,
					"Client Tradeline should link to correct payment")
				# Verify timestamp - should match payment_approved_date
				if import_item.payment_approved_date:
					ct_creation = frappe.db.get_value("Client Tradelines", client_tradeline.name, "creation")
					self.assertEqual(str(ct_creation), str(import_item.payment_approved_date),
						f"Client Tradeline creation time should match payment_approved_date")
				results['client_tradeline']['verified'] = True
			self.assertTrue(results['client_tradeline']['verified'], 
				f"Client Tradeline {import_item.created_tradeline_id} verification failed")
		
		# Check if all verified
		results['all_verified'] = all([
			results['user']['verified'],
			results['customer']['verified'],
			results['cart']['verified'],
			results['payment']['verified'],
			results['client_tradeline']['verified']
		])
		
		return results
	
	# ========== TEST CASES ==========
	
	def test_01_new_customer_single_item(self):
		"""Test Case 1: New customer with single tradeline"""
		print("\n" + "="*80)
		print("TEST 1: New Customer with Single Item")
		print("="*80)
		
		test_email = f"test_user_{frappe.generate_hash(length=8)}@example.com"
		cart_date = add_to_date(now_datetime(), days=-30)
		payment_date = add_to_date(now_datetime(), days=-28)
		
		import_doc = self.create_import_doc([{
			"customer_exists": 0,
			"customer_email": test_email,
			"customer_name": "Test User New",
			"customer_phone": "+1234567890",
			"user_password": "test123",
			"tradeline_id": self.test_data['tradelines'][0],
			"quantity": 1,
			"cart_created_date": cart_date,
			"payment_approved_date": payment_date,
			"payment_status": "Completed",
			"approval_status": "Approved",
			"client_tradeline_status": "Active"
		}])
		
		print(f"Created import: {import_doc.name}")
		
		# Submit
		import_doc.submit()
		frappe.db.commit()
		import_doc.reload()
		
		# Verify
		import_item = import_doc.import_items[0]
		results = self.verify_doctype_creation(import_item)
		
		self.assertTrue(results['all_verified'], "All doctypes should be verified")
		print(f"\n✓ Test 1 Passed - Created:")
		print(f"  User: {results['user']['id']}")
		print(f"  Customer: {results['customer']['id']}")
		print(f"  Cart: {results['cart']['id']}")
		print(f"  Payment: {results['payment']['id']}")
		print(f"  Client Tradeline: {results['client_tradeline']['id']}")
	
	def test_02_existing_customer_single_item(self):
		"""Test Case 2: Existing customer with single tradeline"""
		print("\n" + "="*80)
		print("TEST 2: Existing Customer with Single Item")
		print("="*80)
		
		# Get an existing customer
		existing_customer = frappe.db.get_value("Customer", {}, "name")
		if not existing_customer:
			self.skipTest("No existing customers found")
		
		cart_date = add_to_date(now_datetime(), days=-25)
		payment_date = add_to_date(now_datetime(), days=-23)
		
		import_doc = self.create_import_doc([{
			"customer_exists": 1,
			"existing_customer": existing_customer,
			"tradeline_id": self.test_data['tradelines'][0],
			"quantity": 1,
			"cart_created_date": cart_date,
			"payment_approved_date": payment_date,
			"payment_status": "Completed",
			"approval_status": "Approved",
			"client_tradeline_status": "Active"
		}])
		
		print(f"Created import: {import_doc.name}")
		print(f"Using existing customer: {existing_customer}")
		
		# Submit
		import_doc.submit()
		frappe.db.commit()
		import_doc.reload()
		
		# Verify
		import_item = import_doc.import_items[0]
		results = self.verify_doctype_creation(import_item)
		
		self.assertTrue(results['all_verified'], "All doctypes should be verified")
		self.assertEqual(results['customer']['id'], existing_customer,
			"Should use existing customer")
		print(f"\n✓ Test 2 Passed - Used existing customer: {existing_customer}")
	
	def test_03_multiple_items_same_customer(self):
		"""Test Case 3: Multiple tradelines for same customer"""
		print("\n" + "="*80)
		print("TEST 3: Multiple Items, Same Customer")
		print("="*80)
		
		test_email = f"test_multi_{frappe.generate_hash(length=8)}@example.com"
		cart_date = add_to_date(now_datetime(), days=-20)
		payment_date = add_to_date(now_datetime(), days=-18)
		
		import_doc = self.create_import_doc([
			{
				"customer_exists": 0,
				"customer_email": test_email,
				"customer_name": "Test Multi User",
				"tradeline_id": self.test_data['tradelines'][0],
				"quantity": 1,
				"cart_created_date": cart_date,
				"payment_approved_date": payment_date,
				"payment_status": "Completed",
				"approval_status": "Approved",
				"client_tradeline_status": "Active"
			},
			{
				"customer_exists": 0,
				"customer_email": test_email,
				"customer_name": "Test Multi User",
				"tradeline_id": self.test_data['tradelines'][0],
				"quantity": 2,
				"cart_created_date": cart_date,
				"payment_approved_date": payment_date,
				"payment_status": "Completed",
				"approval_status": "Approved",
				"client_tradeline_status": "Active"
			}
		])
		
		print(f"Created import with 2 items: {import_doc.name}")
		
		# Submit
		import_doc.submit()
		frappe.db.commit()
		import_doc.reload()
		
		# Verify both items
		item1 = import_doc.import_items[0]
		item2 = import_doc.import_items[1]
		
		results1 = self.verify_doctype_creation(item1)
		results2 = self.verify_doctype_creation(item2)
		
		# Should share same customer and cart
		self.assertEqual(results1['customer']['id'], results2['customer']['id'],
			"Both items should use same customer")
		self.assertEqual(results1['cart']['id'], results2['cart']['id'],
			"Both items should share same cart")
		self.assertEqual(results1['payment']['id'], results2['payment']['id'],
			"Both items should share same payment")
		
		# Should have different client tradelines
		self.assertNotEqual(results1['client_tradeline']['id'], results2['client_tradeline']['id'],
			"Each item should create separate client tradeline")
		
		print(f"\n✓ Test 3 Passed:")
		print(f"  Shared Customer: {results1['customer']['id']}")
		print(f"  Shared Cart: {results1['cart']['id']}")
		print(f"  Shared Payment: {results1['payment']['id']}")
		print(f"  Client Tradeline 1: {results1['client_tradeline']['id']}")
		print(f"  Client Tradeline 2: {results2['client_tradeline']['id']}")
	
	def test_04_discount_calculations(self):
		"""Test Case 4: Discount calculations (Percentage and Amount)"""
		print("\n" + "="*80)
		print("TEST 4: Discount Calculations")
		print("="*80)
		
		test_email = f"test_discount_{frappe.generate_hash(length=8)}@example.com"
		cart_date = add_to_date(now_datetime(), days=-15)
		payment_date = add_to_date(now_datetime(), days=-13)
		
		# Get tradeline price
		tradeline_price = frappe.db.get_value("Tradeline", self.test_data['tradelines'][0], "price")
		
		import_doc = self.create_import_doc([
			{
				"customer_exists": 0,
				"customer_email": test_email,
				"customer_name": "Test Discount User",
				"tradeline_id": self.test_data['tradelines'][0],
				"quantity": 1,
				"discount_type": "Percentage",
				"discount_value": 10,
				"cart_created_date": cart_date,
				"payment_approved_date": payment_date,
				"payment_status": "Completed",
				"approval_status": "Approved",
				"client_tradeline_status": "Active"
			}
		])
		
		print(f"Created import with 10% discount: {import_doc.name}")
		
		# Submit
		import_doc.submit()
		frappe.db.commit()
		import_doc.reload()
		
		# Verify
		import_item = import_doc.import_items[0]
		results = self.verify_doctype_creation(import_item)
		
		# Check discount calculations
		cart = frappe.get_doc("Tradeline Cart", results['cart']['id'])
		expected_subtotal = tradeline_price
		expected_discount = tradeline_price * 0.10
		expected_total = expected_subtotal - expected_discount
		
		self.assertAlmostEqual(cart.subtotal, expected_subtotal, places=2,
			msg=f"Subtotal should be {expected_subtotal}")
		self.assertAlmostEqual(cart.discount_amount, expected_discount, places=2,
			msg=f"Discount should be {expected_discount}")
		self.assertAlmostEqual(cart.total_amount, expected_total, places=2,
			msg=f"Total should be {expected_total}")
		
		print(f"\n✓ Test 4 Passed - Discount Calculation:")
		print(f"  Subtotal: ${cart.subtotal:.2f}")
		print(f"  Discount (10%): ${cart.discount_amount:.2f}")
		print(f"  Total: ${cart.total_amount:.2f}")
	
	def test_05_email_suppression(self):
		"""Test Case 5: Email suppression with is_external flag"""
		print("\n" + "="*80)
		print("TEST 5: Email Suppression")
		print("="*80)
		
		test_email = f"test_email_{frappe.generate_hash(length=8)}@example.com"
		cart_date = add_to_date(now_datetime(), days=-10)
		payment_date = add_to_date(now_datetime(), days=-8)
		
		import_doc = self.create_import_doc([{
			"customer_exists": 0,
			"customer_email": test_email,
			"customer_name": "Test Email User",
			"tradeline_id": self.test_data['tradelines'][0],
			"quantity": 1,
			"cart_created_date": cart_date,
			"payment_approved_date": payment_date,
			"payment_status": "Completed",
			"approval_status": "Approved",
			"client_tradeline_status": "Active"
		}], suppress_emails=True)
		
		print(f"Created import with suppress_emails=True: {import_doc.name}")
		
		# Submit
		import_doc.submit()
		frappe.db.commit()
		import_doc.reload()
		
		# Verify is_external flag
		import_item = import_doc.import_items[0]
		results = self.verify_doctype_creation(import_item)
		
		customer = frappe.get_doc("Customer", results['customer']['id'])
		cart = frappe.get_doc("Tradeline Cart", results['cart']['id'])
		payment = frappe.get_doc("Payment Request", results['payment']['id'])
		client_tradeline = frappe.get_doc("Client Tradelines", results['client_tradeline']['id'])
		
		self.assertEqual(customer.is_external, 1, "Customer should have is_external=1")
		self.assertEqual(cart.is_external, 1, "Cart should have is_external=1")
		self.assertEqual(payment.is_external, 1, "Payment should have is_external=1")
		self.assertEqual(client_tradeline.is_external, 1, "Client Tradeline should have is_external=1")
		
		print(f"\n✓ Test 5 Passed - Email Suppression Verified:")
		print(f"  Customer is_external: {customer.is_external}")
		print(f"  Cart is_external: {cart.is_external}")
		print(f"  Payment is_external: {payment.is_external}")
		print(f"  Client Tradeline is_external: {client_tradeline.is_external}")
	
	def test_06_timestamp_accuracy(self):
		"""Test Case 6: Timestamp accuracy for all documents"""
		print("\n" + "="*80)
		print("TEST 6: Timestamp Accuracy")
		print("="*80)
		
		test_email = f"test_timestamp_{frappe.generate_hash(length=8)}@example.com"
		
		# Use specific dates for verification
		cart_date = datetime(2024, 6, 15, 10, 30, 0)
		payment_date = datetime(2024, 6, 15, 14, 20, 0)
		
		import_doc = self.create_import_doc([{
			"customer_exists": 0,
			"customer_email": test_email,
			"customer_name": "Test Timestamp User",
			"tradeline_id": self.test_data['tradelines'][0],
			"quantity": 1,
			"cart_created_date": cart_date,
			"payment_approved_date": payment_date,
			"payment_status": "Completed",
			"approval_status": "Approved",
			"client_tradeline_status": "Active"
		}])
		
		print(f"Created import with specific timestamps: {import_doc.name}")
		print(f"  Cart Date: {cart_date}")
		print(f"  Payment Date: {payment_date}")
		
		# Submit
		import_doc.submit()
		frappe.db.commit()
		import_doc.reload()
		
		# Verify timestamps
		import_item = import_doc.import_items[0]
		results = self.verify_doctype_creation(import_item)
		
		# Get creation times
		user_creation = frappe.db.get_value("User", results['user']['id'], "creation")
		customer_creation = frappe.db.get_value("Customer", results['customer']['id'], "creation")
		cart_creation = frappe.db.get_value("Tradeline Cart", results['cart']['id'], "creation")
		payment_creation = frappe.db.get_value("Payment Request", results['payment']['id'], "creation")
		ct_creation = frappe.db.get_value("Client Tradelines", results['client_tradeline']['id'], "creation")
		
		print(f"\n✓ Test 6 Passed - Timestamps Verified:")
		print(f"  User creation: {user_creation} (expected: {cart_date})")
		print(f"  Customer creation: {customer_creation} (expected: {cart_date})")
		print(f"  Cart creation: {cart_creation} (expected: {cart_date})")
		print(f"  Payment creation: {payment_creation} (expected: {payment_date})")
		print(f"  Client Tradeline creation: {ct_creation} (expected: {payment_date})")
		
		# Verify timestamps match expected dates
		self.assertEqual(str(user_creation), str(cart_date))
		self.assertEqual(str(customer_creation), str(cart_date))
		self.assertEqual(str(cart_creation), str(cart_date))
		self.assertEqual(str(payment_creation), str(payment_date))
		self.assertEqual(str(ct_creation), str(payment_date))
	
	def test_07_validation_fields(self):
		"""Test Case 7: Customer validation fields"""
		print("\n" + "="*80)
		print("TEST 7: Customer Validation Fields")
		print("="*80)
		
		test_email = f"test_validation_{frappe.generate_hash(length=8)}@example.com"
		cart_date = add_to_date(now_datetime(), days=-5)
		payment_date = add_to_date(now_datetime(), days=-3)
		agreement_date = add_to_date(now_datetime(), days=-6)
		questionnaire_date = add_to_date(now_datetime(), days=-6)
		
		import_doc = self.create_import_doc([{
			"customer_exists": 0,
			"customer_email": test_email,
			"customer_name": "Test Validation User",
			"tradeline_id": self.test_data['tradelines'][0],
			"quantity": 1,
			"has_signed_agreement": 1,
			"is_questionnaire_filled": 1,
			"agreement_signed_date": agreement_date,
			"questionnaire_filled_date": questionnaire_date,
			"cart_created_date": cart_date,
			"payment_approved_date": payment_date,
			"payment_status": "Completed",
			"approval_status": "Approved",
			"client_tradeline_status": "Active"
		}])
		
		print(f"Created import with validation fields: {import_doc.name}")
		
		# Submit
		import_doc.submit()
		frappe.db.commit()
		import_doc.reload()
		
		# Verify validation fields
		import_item = import_doc.import_items[0]
		results = self.verify_doctype_creation(import_item)
		
		customer = frappe.get_doc("Customer", results['customer']['id'])
		
		self.assertEqual(customer.has_signed_agreement, 1)
		self.assertEqual(customer.is_questionnaire_filled, 1)
		self.assertEqual(str(customer.agreement_signed_date), str(agreement_date))
		self.assertEqual(str(customer.questionnaire_filled_date), str(questionnaire_date))
		
		print(f"\n✓ Test 7 Passed - Validation Fields:")
		print(f"  Has Signed Agreement: {customer.has_signed_agreement}")
		print(f"  Is Questionnaire Filled: {customer.is_questionnaire_filled}")
		print(f"  Agreement Date: {customer.agreement_signed_date}")
		print(f"  Questionnaire Date: {customer.questionnaire_filled_date}")
	
	def test_08_error_handling_missing_tradeline(self):
		"""Test Case 8: Error handling - Missing tradeline"""
		print("\n" + "="*80)
		print("TEST 8: Error Handling - Missing Tradeline")
		print("="*80)
		
		test_email = f"test_error_{frappe.generate_hash(length=8)}@example.com"
		
		import_doc = self.create_import_doc([{
			"customer_exists": 0,
			"customer_email": test_email,
			"customer_name": "Test Error User",
			"tradeline_id": "INVALID-TRADELINE-ID",
			"quantity": 1,
			"cart_created_date": now_datetime(),
			"payment_approved_date": now_datetime(),
			"payment_status": "Completed",
			"approval_status": "Approved",
			"client_tradeline_status": "Active"
		}])
		
		print(f"Created import with invalid tradeline: {import_doc.name}")
		
		# Try to submit - should fail validation
		with self.assertRaises(Exception) as context:
			import_doc.submit()
			frappe.db.commit()
		
		print(f"\n✓ Test 8 Passed - Validation Error Caught:")
		print(f"  Error: {str(context.exception)}")
	
	def test_09_multiple_customers(self):
		"""Test Case 9: Multiple different customers in one import"""
		print("\n" + "="*80)
		print("TEST 9: Multiple Different Customers")
		print("="*80)
		
		email1 = f"test_cust1_{frappe.generate_hash(length=8)}@example.com"
		email2 = f"test_cust2_{frappe.generate_hash(length=8)}@example.com"
		cart_date = add_to_date(now_datetime(), days=-2)
		payment_date = add_to_date(now_datetime(), days=-1)
		
		import_doc = self.create_import_doc([
			{
				"customer_exists": 0,
				"customer_email": email1,
				"customer_name": "Test Customer 1",
				"tradeline_id": self.test_data['tradelines'][0],
				"quantity": 1,
				"cart_created_date": cart_date,
				"payment_approved_date": payment_date,
				"payment_status": "Completed",
				"approval_status": "Approved",
				"client_tradeline_status": "Active"
			},
			{
				"customer_exists": 0,
				"customer_email": email2,
				"customer_name": "Test Customer 2",
				"tradeline_id": self.test_data['tradelines'][0],
				"quantity": 1,
				"cart_created_date": cart_date,
				"payment_approved_date": payment_date,
				"payment_status": "Completed",
				"approval_status": "Approved",
				"client_tradeline_status": "Active"
			}
		])
		
		print(f"Created import with 2 different customers: {import_doc.name}")
		
		# Submit
		import_doc.submit()
		frappe.db.commit()
		import_doc.reload()
		
		# Verify both customers
		item1 = import_doc.import_items[0]
		item2 = import_doc.import_items[1]
		
		results1 = self.verify_doctype_creation(item1)
		results2 = self.verify_doctype_creation(item2)
		
		# Should have different customers, carts, payments
		self.assertNotEqual(results1['customer']['id'], results2['customer']['id'],
			"Different customers should be created")
		self.assertNotEqual(results1['cart']['id'], results2['cart']['id'],
			"Different carts should be created")
		self.assertNotEqual(results1['payment']['id'], results2['payment']['id'],
			"Different payments should be created")
		
		print(f"\n✓ Test 9 Passed:")
		print(f"  Customer 1: {results1['customer']['id']}")
		print(f"  Customer 2: {results2['customer']['id']}")
		print(f"  Cart 1: {results1['cart']['id']}")
		print(f"  Cart 2: {results2['cart']['id']}")
	
	def test_10_performance_large_import(self):
		"""Test Case 10: Performance with larger import (10 items)"""
		print("\n" + "="*80)
		print("TEST 10: Performance Test - Large Import")
		print("="*80)
		
		test_email = f"test_perf_{frappe.generate_hash(length=8)}@example.com"
		cart_date = add_to_date(now_datetime(), days=-1)
		payment_date = now_datetime()
		
		items = []
		for i in range(10):
			items.append({
				"customer_exists": 0,
				"customer_email": test_email,
				"customer_name": "Test Performance User",
				"tradeline_id": self.test_data['tradelines'][0],
				"quantity": 1,
				"cart_created_date": cart_date,
				"payment_approved_date": payment_date,
				"payment_status": "Completed",
				"approval_status": "Approved",
				"client_tradeline_status": "Active"
			})
		
		import_doc = self.create_import_doc(items)
		
		print(f"Created import with 10 items: {import_doc.name}")
		
		# Submit and time it
		import time
		start_time = time.time()
		import_doc.submit()
		frappe.db.commit()
		end_time = time.time()
		
		processing_time = end_time - start_time
		
		import_doc.reload()
		
		# Verify all items succeeded
		self.assertEqual(import_doc.successful_imports, 10,
			"All 10 items should succeed")
		self.assertEqual(import_doc.failed_imports, 0,
			"No items should fail")
		
		# Verify all items share same cart
		cart_ids = set(item.created_cart_id for item in import_doc.import_items)
		self.assertEqual(len(cart_ids), 1,
			"All items should share one cart")
		
		print(f"\n✓ Test 10 Passed - Performance Test:")
		print(f"  Processing Time: {processing_time:.2f} seconds")
		print(f"  Items per second: {10/processing_time:.2f}")
		print(f"  Successful: {import_doc.successful_imports}")
		print(f"  Failed: {import_doc.failed_imports}")


def run_comprehensive_tests():
	"""Helper function to run all tests from bench console"""
	frappe.init(site="rockettradeline.com")
	frappe.connect()
	
	suite = unittest.TestLoader().loadTestsFromTestCase(TestTradelineImportComprehensive)
	runner = unittest.TextTestRunner(verbosity=2)
	result = runner.run(suite)
	
	frappe.destroy()
	
	return result


if __name__ == "__main__":
	run_comprehensive_tests()

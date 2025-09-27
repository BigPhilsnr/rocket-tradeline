# Copyright (c) 2025, RocketTradeline and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestEmailTemplateCustom(FrappeTestCase):
	def setUp(self):
		"""Set up test data"""
		# Create a test template
		self.test_template = frappe.get_doc({
			"doctype": "Email Template Custom",
			"template_name": "Test Welcome Email",
			"subject": "Welcome {{full_name}}!",
			"description": "Test welcome email template",
			"template_type": "Welcome",
			"is_active": 1,
			"html_content": """
				<h2>Welcome to RocketTradeline!</h2>
				<p>Hello {{full_name}},</p>
				<p>Welcome to our platform. Your account email is: {{email}}</p>
				<p>Thank you for joining us!</p>
			""",
			"parameters": [
				{
					"parameter_name": "full_name",
					"parameter_label": "Full Name",
					"parameter_type": "Data",
					"is_required": 1,
					"description": "User's full name"
				},
				{
					"parameter_name": "email",
					"parameter_label": "Email Address",
					"parameter_type": "Data",
					"is_required": 1,
					"description": "User's email address"
				}
			]
		})
		self.test_template.insert()
	
	def tearDown(self):
		"""Clean up test data"""
		frappe.delete_doc("Email Template Custom", self.test_template.name, force=True)
	
	def test_template_creation(self):
		"""Test template creation and validation"""
		self.assertEqual(self.test_template.template_name, "Test Welcome Email")
		self.assertEqual(len(self.test_template.parameters), 2)
	
	def test_render_content(self):
		"""Test template rendering"""
		context = {
			"full_name": "John Doe",
			"email": "john@example.com"
		}
		
		subject, content = self.test_template.get_rendered_content(context)
		
		self.assertEqual(subject, "Welcome John Doe!")
		self.assertIn("Hello John Doe", content)
		self.assertIn("john@example.com", content)
	
	def test_duplicate_template_name(self):
		"""Test duplicate template name validation"""
		with self.assertRaises(frappe.ValidationError):
			duplicate_template = frappe.get_doc({
				"doctype": "Email Template Custom",
				"template_name": "Test Welcome Email",  # Same name
				"subject": "Another subject",
				"template_type": "Welcome",
				"html_content": "<p>Test</p>"
			})
			duplicate_template.insert()
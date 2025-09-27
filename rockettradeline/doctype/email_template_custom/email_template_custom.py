# Copyright (c) 2025, RocketTradeline and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EmailTemplateCustom(Document):
	def validate(self):
		"""Validate the email template"""
		self.validate_template_name()
		self.validate_parameters()
	
	def validate_template_name(self):
		"""Ensure template name is unique and valid"""
		if not self.template_name:
			frappe.throw("Template Name is required")
		
		# Check for duplicate template names
		existing = frappe.db.exists("Email Template Custom", {
			"template_name": self.template_name,
			"name": ["!=", self.name]
		})
		
		if existing:
			frappe.throw(f"Email template with name '{self.template_name}' already exists")
	
	def validate_parameters(self):
		"""Validate template parameters"""
		if not self.parameters:
			return
		
		parameter_names = []
		for param in self.parameters:
			if not param.parameter_name:
				frappe.throw("Parameter name is required for all parameters")
			
			if param.parameter_name in parameter_names:
				frappe.throw(f"Duplicate parameter name: {param.parameter_name}")
			
			parameter_names.append(param.parameter_name)
	
	def get_rendered_content(self, context=None):
		"""
		Render the email content with provided context
		
		Args:
			context (dict): Dictionary containing parameter values
		
		Returns:
			tuple: (rendered_subject, rendered_content)
		"""
		if not context:
			context = {}
		
		# Get default values for missing parameters
		for param in self.parameters:
			if param.parameter_name not in context:
				context[param.parameter_name] = param.default_value or ""
		
		try:
			# Render subject
			rendered_subject = frappe.render_template(self.subject, context)
			
			# Render HTML content
			rendered_content = frappe.render_template(self.html_content, context)
			
			return rendered_subject, rendered_content
			
		except Exception as e:
			frappe.throw(f"Error rendering template: {str(e)}")
	
	def send_email(self, recipients, context=None, **kwargs):
		"""
		Send email using this template
		
		Args:
			recipients (list): List of email addresses
			context (dict): Context for template rendering
			**kwargs: Additional arguments for frappe.sendmail
		
		Returns:
			bool: True if email was sent successfully
		"""
		try:
			if not self.is_active:
				frappe.throw("Cannot send email using inactive template")
			
			# Render template content
			subject, content = self.get_rendered_content(context)
			
			# Import header and footer functions
			from rockettradeline.api.auth import get_email_header, get_email_footer
			
			# Get recipient for footer (use first recipient if multiple)
			footer_email = recipients[0] if isinstance(recipients, list) else recipients
			
			# Combine header, content, and footer
			email_header = get_email_header()
			email_footer = get_email_footer(footer_email)
			full_content = f"{email_header}{content}{email_footer}"
			
			# Send email
			frappe.sendmail(
				recipients=recipients,
				subject=subject,
				message=full_content,
				**kwargs
			)
			
			# Log the email sending
			frappe.logger().info(f"Email sent using template '{self.template_name}' to {recipients}")
			
			return True
			
		except Exception as e:
			frappe.log_error(f"Email sending failed for template '{self.template_name}': {str(e)}", "Email Template Error")
			return False


@frappe.whitelist()
def get_template_parameters(template_name):
	"""Get parameters for a specific template"""
	try:
		template = frappe.get_doc("Email Template Custom", template_name)
		return {
			"success": True,
			"parameters": [
				{
					"name": param.parameter_name,
					"label": param.parameter_label,
					"type": param.parameter_type,
					"required": param.is_required,
					"default_value": param.default_value,
					"description": param.description
				}
				for param in template.parameters
			]
		}
	except Exception as e:
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def send_template_email(template_name, recipients, context=None):
	"""Send email using template"""
	try:
		template = frappe.get_doc("Email Template Custom", template_name)
		
		if isinstance(recipients, str):
			recipients = [recipients]
		
		if isinstance(context, str):
			import json
			context = json.loads(context)
		
		success = template.send_email(recipients, context)
		
		return {
			"success": success,
			"message": "Email sent successfully" if success else "Email sending failed"
		}
		
	except Exception as e:
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def preview_template(template_name, context=None):
	"""Preview rendered template content"""
	try:
		template = frappe.get_doc("Email Template Custom", template_name)
		
		if isinstance(context, str):
			import json
			context = json.loads(context)
		
		subject, content = template.get_rendered_content(context)
		
		# Import header and footer functions for preview
		from rockettradeline.api.auth import get_email_header, get_email_footer
		
		# Use a sample email for footer
		sample_email = context.get('recipient_email', 'sample@example.com')
		email_header = get_email_header()
		email_footer = get_email_footer(sample_email)
		full_content = f"{email_header}{content}{email_footer}"
		
		return {
			"success": True,
			"subject": subject,
			"content": content,
			"full_content": full_content
		}
		
	except Exception as e:
		return {
			"success": False,
			"error": str(e)
		}
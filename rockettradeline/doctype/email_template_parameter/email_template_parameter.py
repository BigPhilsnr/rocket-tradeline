# Copyright (c) 2025, RocketTradeline and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EmailTemplateParameter(Document):
	def validate(self):
		"""Validate parameter settings"""
		self.validate_parameter_name()
	
	def validate_parameter_name(self):
		"""Validate parameter name format"""
		if not self.parameter_name:
			return
		
		# Parameter name should be a valid Python variable name
		import re
		if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', self.parameter_name):
			frappe.throw(f"Parameter name '{self.parameter_name}' is not valid. Use only letters, numbers, and underscores. Must start with a letter or underscore.")
		
		# Parameter name should not be a Python keyword
		import keyword
		if keyword.iskeyword(self.parameter_name):
			frappe.throw(f"Parameter name '{self.parameter_name}' is a reserved Python keyword. Please use a different name.")
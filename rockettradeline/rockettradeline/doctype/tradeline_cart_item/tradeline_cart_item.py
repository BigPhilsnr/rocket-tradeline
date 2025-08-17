# Copyright (c) 2025, RocketTradeline and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class TradelineCartItem(Document):
	def before_save(self):
		"""Calculate amount before saving"""
		if self.quantity and self.rate:
			self.amount = self.quantity * self.rate
		
		# Get tradeline name if not set
		if self.tradeline and not self.tradeline_name:
			tradeline_doc = frappe.get_doc('Tradeline', self.tradeline)
			self.tradeline_name = tradeline_doc.bank or self.tradeline
	
	def validate(self):
		"""Validate cart item"""
		if self.quantity <= 0:
			frappe.throw("Quantity must be greater than 0")
		
		if self.rate <= 0:
			frappe.throw("Rate must be greater than 0")
		
		# Validate tradeline availability
		if self.tradeline:
			tradeline = frappe.get_doc('Tradeline', self.tradeline)
			if tradeline.status != 'Active':
				frappe.throw(f"Tradeline {self.tradeline} is not active")
			
			if self.quantity > tradeline.max_spots:
				frappe.throw(f"Only {tradeline.max_spots} spots available for {self.tradeline}")

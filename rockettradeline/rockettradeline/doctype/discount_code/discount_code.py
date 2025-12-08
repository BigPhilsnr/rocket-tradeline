# Copyright (c) 2025, RocketTradeline and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, getdate

class DiscountCode(Document):
	def validate(self):
		"""Validate discount code settings"""
		# Ensure code is uppercase
		if self.code:
			self.code = self.code.upper()
		
		# Validate discount value
		if self.discount_type == "Percentage" and self.discount_value > 100:
			frappe.throw("Percentage discount cannot exceed 100%")
		
		if self.discount_value <= 0:
			frappe.throw("Discount value must be greater than 0")
		
		# Validate dates
		if self.valid_from and self.valid_to:
			if getdate(self.valid_to) < getdate(self.valid_from):
				frappe.throw("Valid To date cannot be before Valid From date")
		
		# Validate usage limits
		if self.max_uses and self.max_uses < 0:
			frappe.throw("Max uses cannot be negative")
		
		if self.max_uses_per_user and self.max_uses_per_user < 0:
			frappe.throw("Max uses per user cannot be negative")
	
	def can_be_used(self, user_email=None):
		"""Check if discount code can be used"""
		# Check if enabled
		if not self.enabled:
			return False, "Discount code is disabled"
		
		# Check date validity
		now = now_datetime()
		if self.valid_from and getdate(self.valid_from) > getdate(now):
			return False, "Discount code is not yet valid"
		
		if self.valid_to and getdate(self.valid_to) < getdate(now):
			return False, "Discount code has expired"
		
		# Check max uses
		if self.max_uses:
			current_uses = frappe.db.count('Discount Code Usage', {'discount_code': self.name})
			if current_uses >= self.max_uses:
				return False, "Discount code has reached maximum usage limit"
		
		# Check per-user usage
		if user_email and self.max_uses_per_user:
			user_uses = frappe.db.count('Discount Code Usage', {
				'discount_code': self.name,
				'user_email': user_email
			})
			if user_uses >= self.max_uses_per_user:
				return False, "You have reached the maximum usage limit for this discount code"
		
		# Check minimum cart amount
		# This will be checked when applying to cart
		
		return True, "Discount code is valid"
	
	def calculate_discount(self, cart_subtotal):
		"""Calculate discount amount based on cart subtotal"""
		# Check minimum amount
		if self.minimum_cart_amount and cart_subtotal < self.minimum_cart_amount:
			return 0, f"Cart subtotal must be at least {self.minimum_cart_amount} to use this discount code"
		
		if self.discount_type == "Amount":
			discount_amount = self.discount_value
		elif self.discount_type == "Percentage":
			discount_amount = (cart_subtotal * self.discount_value) / 100
		else:
			return 0, "Invalid discount type"
		
		# Apply maximum discount limit if set
		if self.max_discount_amount and discount_amount > self.max_discount_amount:
			discount_amount = self.max_discount_amount
		
		return discount_amount, "Discount calculated successfully"
	
	def record_usage(self, cart_id, user_email):
		"""Record usage of discount code"""
		usage = frappe.get_doc({
			'doctype': 'Discount Code Usage',
			'discount_code': self.name,
			'code': self.code,
			'cart_id': cart_id,
			'user_email': user_email,
			'discount_amount': 0,  # Will be updated when cart is finalized
			'used_at': now_datetime()
		})
		usage.insert()
		return usage

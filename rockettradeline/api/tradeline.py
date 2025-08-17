from rockettradeline.api.auth import jwt_required, get_current_user
import frappe
from frappe import _
import json
from .utils import validate_tradeline_data, get_user_permissions, log_api_call, get_pagination_info, sanitize_search_term

# Tradeline APIs

@frappe.whitelist(allow_guest=True)
def get_tradelines(limit=20, start=0, search=None, filters=None):
    """
    Get list of tradelines
    """
    try:
        query_filters = {"status": "Active"}
        
        if search:
            query_filters["bank"] = ["like", f"%{search}%"]
        
        if filters:
            if isinstance(filters, str):
                filters = json.loads(filters)
            
            if filters.get("min_price"):
                query_filters["price"] = [">=", filters["min_price"]]
            if filters.get("max_price"):
                query_filters["price"] = ["<=", filters["max_price"]]
            if filters.get("min_credit_limit"):
                query_filters["credit_limit"] = [">=", filters["min_credit_limit"]]
            if filters.get("bank"):
                query_filters["bank"] = filters["bank"]
        
        tradelines = frappe.get_all("Tradeline",
            filters=query_filters,
            fields=["name", "bank", "age_year", "age_month", "credit_limit", 
                   "price", "max_spots", "remaining_spots", "closing_date", 
                   "credit_utilization_rate", "status"],
            limit=limit,
            start=start,
            order_by="creation desc"
        )
        
        # Get bank names
        for tradeline in tradelines:
            if tradeline.bank:
                bank_doc = frappe.get_doc("Tradeline Bank", tradeline.bank)
                tradeline.bank_name = bank_doc.bank_name
        
        return {
            "success": True,
            "tradelines": tradelines
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist(allow_guest=True)
def get_tradeline(tradeline_id):
    """
    Get tradeline details
    """
    try:
        tradeline = frappe.get_doc("Tradeline", tradeline_id)
        
        # Get related data
        bank_doc = frappe.get_doc("Tradeline Bank", tradeline.bank) if tradeline.bank else None
        card_holder_doc = frappe.get_doc("Card Holder", tradeline.card_holder) if tradeline.card_holder else None
        mailing_address_doc = frappe.get_doc("Mailing Address", tradeline.mailing_address) if tradeline.mailing_address else None
        
        result = {
            "name": tradeline.name,
            "bank": tradeline.bank,
            "bank_name": bank_doc.bank_name if bank_doc else None,
            "age_year": tradeline.age_year,
            "age_month": tradeline.age_month,
            "credit_limit": tradeline.credit_limit,
            "price": tradeline.price,
            "max_spots": tradeline.max_spots,
            "remaining_spots": tradeline.remaining_spots,
            "purchased_spots": tradeline.purchased_spots,
            "closing_date": tradeline.closing_date,
            "credit_utilization_rate": tradeline.credit_utilization_rate,
            "status": tradeline.status,
            "balance": tradeline.balance,
            "card_holder": {
                "name": card_holder_doc.name if card_holder_doc else None,
                "fullname": card_holder_doc.fullname if card_holder_doc else None,
                "email": card_holder_doc.email if card_holder_doc else None,
                "phone": card_holder_doc.phone if card_holder_doc else None
            } if card_holder_doc else None,
            "mailing_address": {
                "name": mailing_address_doc.name if mailing_address_doc else None,
                # Add mailing address fields when available
            } if mailing_address_doc else None
        }
        
        return {
            "success": True,
            "tradeline": result
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def create_tradeline(bank, age_year, credit_limit, price, max_spots, 
                    closing_date, card_holder, mailing_address, 
                    age_month=None, credit_utilization_rate=None, 
                    balance=None, status="Active"):
    """
    Create new tradeline
    """
    try:
        user = get_current_user()
        if not user or not frappe.has_permission("Tradeline", "create"):
            return {
                "success": False,
                "message": "Permission denied"
            }
        
        tradeline = frappe.get_doc({
            "doctype": "Tradeline",
            "bank": bank,
            "age_year": age_year,
            "age_month": age_month or 0,
            "credit_limit": credit_limit,
            "price": price,
            "max_spots": max_spots,
            "remaining_spots": max_spots,
            "purchased_spots": 0,
            "closing_date": closing_date,
            "card_holder": card_holder,
            "mailing_address": mailing_address,
            "credit_utilization_rate": credit_utilization_rate or 0,
            "balance": balance or 0,
            "status": status
        })
        tradeline.insert()
        return {
            "success": True,
            "message": "Tradeline created successfully",
            "tradeline": {
                "name": tradeline.name,
                "bank": tradeline.bank,
                "status": tradeline.status
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def update_tradeline(tradeline_id, **kwargs):
    """
    Update existing tradeline
    """
    try:
        user = get_current_user()
        if not user or not frappe.has_permission("Tradeline", "write"):
            return {
                "success": False,
                "message": "Permission denied"
            }
        
        tradeline = frappe.get_doc("Tradeline", tradeline_id)
        
        # Update fields
        allowed_fields = ["bank", "age_year", "age_month", "credit_limit", 
                         "price", "max_spots", "closing_date", "card_holder",
                         "mailing_address", "credit_utilization_rate", 
                         "balance", "status"]
        
        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                setattr(tradeline, field, value)
        
        tradeline.save()
        
        return {
            "success": True,
            "message": "Tradeline updated successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def delete_tradeline(tradeline_id):
    """
    Delete tradeline
    """
    try:
        user = frappe.session.user
        if not user or not frappe.has_permission("Tradeline", "delete"):
            return {
                "success": False,
                "message": "Permission denied"
            }
        
        frappe.delete_doc("Tradeline", tradeline_id)
        
        return {
            "success": True,
            "message": "Tradeline deleted successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def change_tradeline_status(tradeline_id, status):
    """
    Change tradeline status
    """
    try:
        user = frappe.session.user
        if not user or not frappe.has_permission("Tradeline", "write"):
            return {
                "success": False,
                "message": "Permission denied"
            }
        
        if status not in ["Active", "InActive"]:
            return {
                "success": False,
                "message": "Invalid status"
            }
        
        tradeline = frappe.get_doc("Tradeline", tradeline_id)
        tradeline.status = status
        tradeline.save()
        
        return {
            "success": True,
            "message": f"Tradeline status changed to {status}"
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }

# Supporting APIs

@frappe.whitelist(allow_guest=True)
def get_banks():
    """
    Get list of banks
    """
    try:
        banks = frappe.get_all("Tradeline Bank", 
            fields=["name", "bank_name", "image"],
            order_by="bank_name asc"
        )
        return {
            "success": True,
            "banks": banks
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def create_bank(bank_name):
    """
    Create new bank
    """
    user = frappe.session.user
    if not user or not frappe.has_permission("Tradeline Bank", "create"):
        return {
            "success": False,
            "message": "Permission denied"
        }
    bank = frappe.get_doc({
        "doctype": "Tradeline Bank",
        "bank_name": bank_name
    })
    bank.insert()
    return {
        "success": True,
        "message": "Bank created successfully",
        "bank": {
            "name": bank.name,
            "bank_name": bank.bank_name
        }
    }

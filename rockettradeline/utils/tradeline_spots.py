# Copyright (c) 2025, RocketTradeline and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def recalculate_tradeline_remaining_spots(tradeline_name):
    """
    Recalculate remaining spots for a tradeline based on:
    1. Pending Approval Payment Requests (spots are considered taken)
    2. Active Client Tradelines (spots are taken)
    3. Rejected Payment Requests (spots are released)
    4. Expired/Refunded Client Tradelines (spots are released)
    
    Args:
        tradeline_name (str): The name/ID of the Tradeline document
        
    Returns:
        dict: Updated spots information
    """
    try:
        # Get the tradeline document
        tradeline_doc = frappe.get_doc("Tradeline", tradeline_name)
        max_spots = int(tradeline_doc.max_spots or 0)
        
        # Initialize spots counter
        taken_spots = 0
        
        # 1. Count spots from Pending Approval Payment Requests
        # Get all payment requests with status "Pending Approval"
        pending_payment_requests = frappe.get_all(
            "Payment Request",
            filters={
                "status": "Pending Approval"
            },
            fields=["name", "cart_id"]
        )
        
        for pr in pending_payment_requests:
            if not pr.cart_id:
                continue
                
            # Get cart items for this payment request
            try:
                cart_doc = frappe.get_doc("Tradeline Cart", pr.cart_id)
                for item in cart_doc.items:
                    if item.tradeline == tradeline_name:
                        taken_spots += int(item.quantity or 0)
            except Exception:
                continue
        
        # 2. Count spots from Active Client Tradelines
        # Get all client tradelines with statuses that indicate spots are taken
        active_statuses = ["Active", "Pending AU", "Inactive"]
        
        active_client_tradelines = frappe.get_all(
            "Client Tradelines",
            filters={
                "tradeline": tradeline_name,
                "status": ["in", active_statuses]
            },
            fields=["quantity"]
        )
        
        for ct in active_client_tradelines:
            taken_spots += int(ct.quantity or 0)
        
        # 3. Calculate remaining spots
        remaining_spots = max_spots - taken_spots
        remaining_spots = max(0, remaining_spots)  # Ensure it doesn't go below 0
        
        # 4. Update the tradeline document
        tradeline_doc.purchased_spots = taken_spots
        tradeline_doc.remaining_spots = remaining_spots
        
        # Save without triggering hooks to avoid recursion
        tradeline_doc.save(ignore_permissions=True)
        frappe.db.commit()
        
        return {
            "success": True,
            "tradeline": tradeline_name,
            "max_spots": max_spots,
            "taken_spots": taken_spots,
            "remaining_spots": remaining_spots
        }
        
    except Exception as e:
        frappe.log_error(
            f"Error recalculating remaining spots for tradeline {tradeline_name}: {str(e)}",
            "Tradeline Spots Recalculation Error"
        )
        return {
            "success": False,
            "error": str(e),
            "tradeline": tradeline_name
        }


def recalculate_all_tradeline_spots_from_payment_request(payment_request_name):
    """
    Recalculate spots for all tradelines in a payment request's cart
    
    Args:
        payment_request_name (str): The name/ID of the Payment Request document
    """
    try:
        payment_request_doc = frappe.get_doc("Payment Request", payment_request_name)
        
        if not payment_request_doc.cart_id:
            return {"success": False, "error": "No cart linked to payment request"}
        
        # Get cart items
        cart_doc = frappe.get_doc("Tradeline Cart", payment_request_doc.cart_id)
        tradelines_updated = []
        
        for item in cart_doc.items:
            if item.tradeline:
                result = recalculate_tradeline_remaining_spots(item.tradeline)
                tradelines_updated.append(result)
        
        return {
            "success": True,
            "payment_request": payment_request_name,
            "tradelines_updated": tradelines_updated
        }
        
    except Exception as e:
        frappe.log_error(
            f"Error recalculating spots from payment request {payment_request_name}: {str(e)}",
            "Payment Request Spots Recalculation Error"
        )
        return {
            "success": False,
            "error": str(e)
        }


def recalculate_spots_from_client_tradeline(client_tradeline_name):
    """
    Recalculate spots for the tradeline linked to a client tradeline
    
    Args:
        client_tradeline_name (str): The name/ID of the Client Tradelines document
    """
    try:
        client_tradeline_doc = frappe.get_doc("Client Tradelines", client_tradeline_name)
        
        if not client_tradeline_doc.tradeline:
            return {"success": False, "error": "No tradeline linked"}
        
        result = recalculate_tradeline_remaining_spots(client_tradeline_doc.tradeline)
        
        return {
            "success": True,
            "client_tradeline": client_tradeline_name,
            "tradeline_result": result
        }
        
    except Exception as e:
        frappe.log_error(
            f"Error recalculating spots from client tradeline {client_tradeline_name}: {str(e)}",
            "Client Tradeline Spots Recalculation Error"
        )
        return {
            "success": False,
            "error": str(e)
        }


def check_tradeline_availability(tradeline_name, requested_quantity):
    """
    Check if a tradeline has enough available spots for the requested quantity
    
    Args:
        tradeline_name (str): The name/ID of the Tradeline document
        requested_quantity (int): Number of spots requested
        
    Returns:
        dict: Availability status and details
    """
    try:
        # First recalculate to get the most up-to-date numbers
        recalculate_result = recalculate_tradeline_remaining_spots(tradeline_name)
        
        if not recalculate_result.get("success"):
            return {
                "available": False,
                "error": "Could not calculate availability"
            }
        
        remaining_spots = recalculate_result.get("remaining_spots", 0)
        requested_quantity = int(requested_quantity)
        
        is_available = remaining_spots >= requested_quantity
        
        return {
            "available": is_available,
            "tradeline": tradeline_name,
            "requested_quantity": requested_quantity,
            "remaining_spots": remaining_spots,
            "max_spots": recalculate_result.get("max_spots", 0),
            "taken_spots": recalculate_result.get("taken_spots", 0)
        }
        
    except Exception as e:
        frappe.log_error(
            f"Error checking availability for tradeline {tradeline_name}: {str(e)}",
            "Tradeline Availability Check Error"
        )
        return {
            "available": False,
            "error": str(e)
        }


def check_cart_availability(cart_id):
    """
    Check if all tradelines in a cart have enough available spots
    
    Args:
        cart_id (str): The name/ID of the Tradeline Cart document
        
    Returns:
        dict: Availability status for all items in cart
    """
    try:
        cart_doc = frappe.get_doc("Tradeline Cart", cart_id)
        
        if not cart_doc.items:
            return {
                "available": False,
                "error": "Cart is empty"
            }
        
        availability_results = []
        all_available = True
        
        for item in cart_doc.items:
            if item.tradeline and item.quantity:
                result = check_tradeline_availability(item.tradeline, item.quantity)
                availability_results.append(result)
                
                if not result.get("available"):
                    all_available = False
        
        return {
            "available": all_available,
            "cart_id": cart_id,
            "items": availability_results
        }
        
    except Exception as e:
        frappe.log_error(
            f"Error checking cart availability {cart_id}: {str(e)}",
            "Cart Availability Check Error"
        )
        return {
            "available": False,
            "error": str(e)
        }


@frappe.whitelist()
def recalculate_all_tradelines():
    """
    Recalculate remaining spots for all active tradelines
    Can be called manually or by scheduler
    """
    try:
        tradelines = frappe.get_all(
            "Tradeline",
            filters={"status": "Active"},
            pluck="name"
        )
        
        results = []
        for tradeline in tradelines:
            result = recalculate_tradeline_remaining_spots(tradeline)
            results.append(result)
        
        return {
            "success": True,
            "total_tradelines": len(tradelines),
            "results": results
        }
        
    except Exception as e:
        frappe.log_error(
            f"Error recalculating all tradelines: {str(e)}",
            "All Tradelines Recalculation Error"
        )
        return {
            "success": False,
            "error": str(e)
        }

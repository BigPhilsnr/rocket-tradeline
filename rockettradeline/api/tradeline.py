from rockettradeline.api.auth import jwt_required, get_current_user
import frappe
from frappe import _
import json
from .utils import is_administrator, get_authenticated_user
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
            if filters.get("status"):
                query_filters["status"] = filters["status"]

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
@jwt_required()
def get_tradeline_admin(tradeline_id):
    """
    Get tradeline details
    """
    try:
        
        if not is_administrator(get_authenticated_user()):
            frappe.throw(_("You do not have permission to access this resource"), frappe.PermissionError)
            
        tradeline = frappe.get_doc("Tradeline", tradeline_id)
        
        # Get related data
        bank_doc = frappe.get_doc("Tradeline Bank", tradeline.bank) if tradeline.bank else None
        card_holder_doc = frappe.get_doc("Customer", tradeline.card_holder) if tradeline.card_holder else None
        # mailing_address_doc = frappe.get_doc("Mailing Address", tradeline.mailing_address) if tradeline.mailing_address else None
        
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
                "fullname": card_holder_doc.customer_name if card_holder_doc else None,
                "email": card_holder_doc.email_id if card_holder_doc else None,
                "phone": card_holder_doc.mobile_no if card_holder_doc else None
            } if card_holder_doc else None,
            "mailing_address": {
                "name": card_holder_doc.primary_address if card_holder_doc else None,
                # Add mailing address fields when available
            } if card_holder_doc else None
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

@frappe.whitelist(allow_guest=True)
def get_tradeline(tradeline_id):
    """
    Get tradeline details
    """
    try:
        tradeline = frappe.get_doc("Tradeline", tradeline_id)
        
        # Get related data
        bank_doc = frappe.get_doc("Tradeline Bank", tradeline.bank) if tradeline.bank else None
        card_holder_doc = frappe.get_doc("Customer", tradeline.card_holder) if tradeline.card_holder else None
        # mailing_address_doc = frappe.get_doc("Mailing Address", tradeline.mailing_address) if tradeline.mailing_address else None
        
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

        status = status if is_administrator(user) else "InActive"

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

@frappe.whitelist(allow_guest=True)
@jwt_required()
def update_tradeline(tradeline_id, **kwargs):
    """
    Update existing tradeline
    """
    try:
        
        user = get_authenticated_user()
      
        
        tradeline = frappe.get_doc("Tradeline", tradeline_id)
        if (not is_administrator(user)) and tradeline.get('owner') != user :
            frappe.throw(_("You do not have permission to access this resource"), frappe.PermissionError)

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

@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_tradeline_activity(tradeline_name):
    """
    Get activity timeline for a specific tradeline
    Returns date and activity information from various related documents
    """
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.throw(_("Authentication required"))

        # Check if user has permission to view this tradeline
        if not is_administrator(current_user):
            frappe.throw(_("Access denied. Only administrators can view tradeline activity."))

        # Validate that the tradeline exists
        if not frappe.db.exists("Tradeline", tradeline_name):
            return {
                "success": False,
                "message": "Tradeline not found"
            }

        activities = []

        # Get tradeline creation and modification activities
        tradeline_doc = frappe.get_doc("Tradeline", tradeline_name)
        
        # Add creation activity
        activities.append({
            "date": tradeline_doc.creation,
            "activity": f"Tradeline created",
            "type": "creation",
            "reference_doctype": "Tradeline",
            "reference_name": tradeline_name,
            "user": tradeline_doc.owner,
            "details": {
                "bank": tradeline_doc.bank,
                "credit_limit": tradeline_doc.credit_limit,
                "price": tradeline_doc.price,
                "status": tradeline_doc.status
            }
        })

        # Add modification activity if different from creation
        if tradeline_doc.modified != tradeline_doc.creation:
            activities.append({
                "date": tradeline_doc.modified,
                "activity": f"Tradeline updated",
                "type": "modification",
                "reference_doctype": "Tradeline",
                "reference_name": tradeline_name,
                "user": tradeline_doc.modified_by,
                "details": {
                    "current_status": tradeline_doc.status,
                    "remaining_spots": tradeline_doc.remaining_spots,
                    "purchased_spots": tradeline_doc.purchased_spots
                }
            })

        # Get Client Tradelines activities (purchases)
        client_tradelines = frappe.get_all("Client Tradelines",
            filters={"tradeline": tradeline_name},
            fields=["name", "customer", "customer_name", "status", "quantity", 
                   "total_amount", "creation", "modified", "owner", "modified_by"],
            order_by="creation desc"
        )

        for client_tradeline in client_tradelines:
            # Purchase activity
            activities.append({
                "date": client_tradeline.creation,
                "activity": f"Tradeline purchased by {client_tradeline.customer_name}",
                "type": "purchase",
                "reference_doctype": "Client Tradelines",
                "reference_name": client_tradeline.name,
                "user": client_tradeline.owner,
                "details": {
                    "customer": client_tradeline.customer,
                    "customer_name": client_tradeline.customer_name,
                    "quantity": client_tradeline.quantity,
                    "amount": client_tradeline.total_amount,
                    "status": client_tradeline.status
                }
            })

            # Status change activity if modified
            if client_tradeline.modified != client_tradeline.creation:
                activities.append({
                    "date": client_tradeline.modified,
                    "activity": f"Client tradeline status updated to {client_tradeline.status}",
                    "type": "status_change",
                    "reference_doctype": "Client Tradelines",
                    "reference_name": client_tradeline.name,
                    "user": client_tradeline.modified_by,
                    "details": {
                        "customer_name": client_tradeline.customer_name,
                        "new_status": client_tradeline.status
                    }
                })

        # Get Tradeline Cart activities
        cart_items = frappe.db.sql("""
            SELECT 
                tc.name as cart_name,
                tc.user_id,
                tc.customer,
                tc.status as cart_status,
                tc.creation,
                tc.modified,
                tc.owner,
                tc.modified_by,
                tci.quantity,
                tci.amount
            FROM `tabTradeline Cart` tc
            INNER JOIN `tabTradeline Cart Item` tci ON tc.name = tci.parent
            WHERE tci.tradeline = %s
            ORDER BY tc.creation DESC
        """, (tradeline_name,), as_dict=True)

        for cart_item in cart_items:
            # Cart addition activity
            activities.append({
                "date": cart_item.creation,
                "activity": f"Added to cart by {cart_item.user_id}",
                "type": "cart_addition",
                "reference_doctype": "Tradeline Cart",
                "reference_name": cart_item.cart_name,
                "user": cart_item.owner,
                "details": {
                    "user_id": cart_item.user_id,
                    "customer": cart_item.customer,
                    "quantity": cart_item.quantity,
                    "amount": cart_item.amount,
                    "cart_status": cart_item.cart_status
                }
            })

        # Get Payment Request activities related to this tradeline
        payment_requests = frappe.db.sql("""
            SELECT DISTINCT
                pr.name,
                pr.customer_email,
                pr.payment_method,
                pr.status,
                pr.total_amount,
                pr.creation,
                pr.modified,
                pr.owner,
                pr.modified_by
            FROM `tabPayment Request` pr
            INNER JOIN `tabTradeline Cart` tc ON pr.cart_id = tc.name
            INNER JOIN `tabTradeline Cart Item` tci ON tc.name = tci.parent
            WHERE tci.tradeline = %s
            ORDER BY pr.creation DESC
        """, (tradeline_name,), as_dict=True)

        for payment in payment_requests:
            # Payment creation activity
            activities.append({
                "date": payment.creation,
                "activity": f"Payment request created by {payment.customer_email}",
                "type": "payment_request",
                "reference_doctype": "Payment Request",
                "reference_name": payment.name,
                "user": payment.owner,
                "details": {
                    "customer_email": payment.customer_email,
                    "payment_method": payment.payment_method,
                    "amount": payment.total_amount,
                    "status": payment.status
                }
            })

            # Payment status change if modified
            if payment.modified != payment.creation:
                activities.append({
                    "date": payment.modified,
                    "activity": f"Payment status updated to {payment.status}",
                    "type": "payment_status",
                    "reference_doctype": "Payment Request",
                    "reference_name": payment.name,
                    "user": payment.modified_by,
                    "details": {
                        "customer_email": payment.customer_email,
                        "payment_status": payment.status,
                        "amount": payment.total_amount
                    }
                })

        # Get any Version/Document history activities
        versions = frappe.get_all("Version",
            filters={"ref_doctype": "Tradeline", "docname": tradeline_name},
            fields=["name", "creation", "owner", "data"],
            order_by="creation desc",
            limit=20
        )

        for version in versions:
            try:
                import json
                version_data = json.loads(version.data) if version.data else {}
                changed_fields = version_data.get("changed", [])
                
                if changed_fields:
                    field_changes = [field[0] for field in changed_fields if len(field) > 0]
                    activities.append({
                        "date": version.creation,
                        "activity": f"Fields updated: {', '.join(field_changes)}",
                        "type": "field_update",
                        "reference_doctype": "Version",
                        "reference_name": version.name,
                        "user": version.owner,
                        "details": {
                            "changed_fields": field_changes,
                            "version_name": version.name
                        }
                    })
            except:
                # Skip if version data can't be parsed
                pass

        # Sort all activities by date (newest first)
        activities.sort(key=lambda x: x["date"], reverse=True)

        # Get summary statistics
        total_activities = len(activities)
        activity_types = {}
        users_involved = set()
        
        for activity in activities:
            activity_type = activity["type"]
            activity_types[activity_type] = activity_types.get(activity_type, 0) + 1
            if activity["user"]:
                users_involved.add(activity["user"])

        return {
            "success": True,
            "tradeline_name": tradeline_name,
            "activities": activities,
            "summary": {
                "total_activities": total_activities,
                "activity_types": activity_types,
                "users_involved": list(users_involved),
                "date_range": {
                    "earliest": activities[-1]["date"] if activities else None,
                    "latest": activities[0]["date"] if activities else None
                }
            },
            "tradeline_info": {
                "name": tradeline_doc.name,
                "bank": tradeline_doc.bank,
                "status": tradeline_doc.status,
                "credit_limit": tradeline_doc.credit_limit,
                "remaining_spots": tradeline_doc.remaining_spots,
                "purchased_spots": tradeline_doc.purchased_spots
            }
        }

    except Exception as e:
        frappe.log_error(f"Error fetching tradeline activity for {tradeline_name}: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch tradeline activity: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
def get_tradeline_comments(tradeline_name):
    """
    Get timeline contents for a specific tradeline
    Returns timeline items similar to Frappe's prepare_timeline_contents
    """
    try:
        # Validate that the tradeline exists
        if not frappe.db.exists("Tradeline", tradeline_name):
            return {
                "success": False,
                "message": "Tradeline not found"
            }

        # Get tradeline document
        tradeline_doc = frappe.get_doc("Tradeline", tradeline_name)
        
        timeline_items = []

        # Add creation message (similar to get_creation_message)
        timeline_items.append({
            "creation": tradeline_doc.creation,
            "content": f"{tradeline_doc.owner} created this tradeline",
            "icon": "es-line-plus",
            "icon_size": "sm"
        })

        # Add modified message (similar to get_modified_message)
        if tradeline_doc.modified != tradeline_doc.creation:
            timeline_items.append({
                "creation": tradeline_doc.modified,
                "content": f"{tradeline_doc.modified_by} last edited this",
                "icon": "es-line-edit",
                "icon_size": "sm"
            })

        # Get version timeline contents (similar to get_version_timeline_contents)
        versions = frappe.get_all("Version",
            filters={"ref_doctype": "Tradeline", "docname": tradeline_name},
            fields=["name", "creation", "owner", "data"],
            order_by="creation desc",
            limit=20
        )

        for version in versions:
            try:
                import json
                version_data = json.loads(version.data) if version.data else {}
                changed_fields = version_data.get("changed", [])
                
                if changed_fields:
                    # Format changed fields for display
                    field_changes = []
                    for change in changed_fields:
                        if len(change) >= 2:
                            field_name = change[0]
                            # Get field label from meta if available
                            try:
                                field_label = frappe.get_meta("Tradeline").get_field(field_name).label or field_name
                            except:
                                field_label = field_name.replace("_", " ").title()
                            field_changes.append(field_label)
                    
                    if field_changes:
                        timeline_items.append({
                            "creation": version.creation,
                            "content": f"<a href='#Form/User/{version.owner}'>{version.owner}</a> changed {', '.join(field_changes)}",
                            "icon": "es-line-clock",
                            "icon_size": "sm",
                            "doctype": "Version",
                            "name": version.name
                        })
            except:
                # Skip if version data can't be parsed
                continue

        # Sort timeline items by creation date (newest first)
        timeline_items.sort(key=lambda x: x["creation"], reverse=True)

        # Get basic statistics
        total_items = len(timeline_items)
        latest_activity = timeline_items[0]["creation"] if timeline_items else None
        oldest_activity = timeline_items[-1]["creation"] if timeline_items else None

        return {
            "success": True,
            "tradeline_name": tradeline_name,
            "timeline_items": timeline_items,
            "statistics": {
                "total_items": total_items,
                "latest_activity": latest_activity,
                "oldest_activity": oldest_activity
            },
    
        }

    except Exception as e:
        frappe.log_error(f"Error fetching tradeline timeline for {tradeline_name}: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to fetch tradeline timeline: {str(e)}"
        }

@frappe.whitelist(allow_guest=True)
@jwt_required()
def add_tradeline_comment(tradeline_name, content, comment_type="Comment"):
    """
    Add a comment to a specific tradeline
    """
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.throw(_("Authentication required"))

        # Check if user has permission to comment on this tradeline
        if not is_administrator(current_user):
            frappe.throw(_("Access denied. Only administrators can add comments to tradelines."))

        # Validate that the tradeline exists
        if not frappe.db.exists("Tradeline", tradeline_name):
            return {
                "success": False,
                "message": "Tradeline not found"
            }

        if not content or not content.strip():
            return {
                "success": False,
                "message": "Comment content is required"
            }

        # Create the comment
        comment_doc = frappe.get_doc({
            "doctype": "Comment",
            "comment_type": comment_type,
            "reference_doctype": "Tradeline",
            "reference_name": tradeline_name,
            "content": content.strip(),
            "comment_email": current_user,
            "comment_by": frappe.db.get_value("User", current_user, "full_name") or current_user
        })
        
        comment_doc.insert(ignore_permissions=True)
        frappe.db.commit()

        return {
            "success": True,
            "message": "Comment added successfully",
            "comment": {
                "name": comment_doc.name,
                "content": comment_doc.content,
                "comment_type": comment_doc.comment_type,
                "date": comment_doc.creation,
                "user": current_user
            }
        }

    except Exception as e:
        frappe.log_error(f"Error adding comment to tradeline {tradeline_name}: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to add comment: {str(e)}"
        }

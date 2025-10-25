import frappe
from frappe import _
from frappe.utils import flt, now_datetime, getdate
from .auth import jwt_required, get_authenticated_user, get_email_header, get_email_footer
from .utils import is_administrator
from rockettradeline.rockettradeline.doctype.email_template_custom.email_template_custom import send_email_template


@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_client_tradelines(status=None, limit=20, start=0, customer=None, tradeline=None):
    """Get client tradelines based on user permissions"""
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.throw(_("Authentication required"))

        # Check if user is administrator
        is_admin = is_administrator(current_user)
        
        # Build base query conditions
        conditions = []
        values = []
        
        # If not admin, filter by customer email
        if not is_admin:
            # Find customer record for current user
            customer_records = frappe.get_all("Customer", 
                filters={"email_id": current_user}, 
                fields=["name", "customer_name"])
            
            customer_record2 = frappe.get_all("Customer", 
            filters= { "account_manager": current_user}, 
            fields=["name", "customer_name"])
            customer_records += customer_record2
     
            
            if not customer_records:
                return {
                    "success": True,
                    "data": [],
                    "total": 0,
                    "message": "No customer record found for current user"
                }
            
            customer_names = [rec.name for rec in customer_records]
            customer_placeholders = ", ".join(["%s"] * len(customer_names))
            conditions.append(f"customer IN ({customer_placeholders})")
            values.extend(customer_names)
        else:
            # Admin can optionally filter by specific customer
            if customer:
                conditions.append("customer = %s")
                values.append(customer)
        
        # Add status filter if provided
        if status:
            conditions.append("status = %s")
            values.append(status)

        # Add tradeline_id filter if provided
        if tradeline:
            conditions.append("tradeline = %s")
            values.append(tradeline)

        # Build WHERE clause
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
        
        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total
            FROM `tabClient Tradelines` ct
            LEFT JOIN `tabTradeline` t ON ct.tradeline = t.name
            LEFT JOIN `tabTradeline Bank` tb ON t.bank = tb.name
            {where_clause}
        """
        
        total_result = frappe.db.sql(count_query, values, as_dict=True)
        total = total_result[0].total if total_result else 0
        
        # Get paginated results with tradeline details
        query = f"""
            SELECT 
                ct.name,
                ct.title,
                ct.customer,
                ct.customer_name,
                ct.status,
                ct.created_date,
                ct.cart,
                ct.payment_request,
                ct.tradeline,
                ct.tradeline_name,
                ct.quantity,
                ct.unit_price,
                ct.total_amount,
                ct.notes,
                ct.expiry_date,
                ct.assigned_to,
                ct.completion_date,
                ct.creation,
                ct.modified,
                ct.commission_paid,
                ct.refund_username,
                ct.refund_security_question,
                ct.refund_security_answer,
                ct.refund_pin,
                ct.refund_reason,
                ct.refund_link,
                ct.swapped,
                ct.swapped_on,
                t.bank,
                tb.bank_name,
                tb.image as bank_logo,
                t.credit_limit,
                t.age_year,
                t.commission,
                t.age_month,
                t.closing_date
            FROM `tabClient Tradelines` ct
            LEFT JOIN `tabTradeline` t ON ct.tradeline = t.name
            LEFT JOIN `tabTradeline Bank` tb ON t.bank = tb.name
            {where_clause}
            ORDER BY modified DESC
            LIMIT %s OFFSET %s
        """
        
        values.extend([int(limit), int(start)])
        
        tradelines = frappe.db.sql(query, values, as_dict=True)
        
        # Format the response
        formatted_tradelines = []
        for tradeline in tradelines:
            formatted_tradeline = {
                "id": tradeline.name,
                "title": tradeline.title,
                "customer": tradeline.customer,
                "customer_name": tradeline.customer_name,
                "status": tradeline.status,
                "created_date": tradeline.created_date,
                "cart_id": tradeline.cart,
                "payment_request_id": tradeline.payment_request,
                "tradeline": tradeline.tradeline,
                "tradeline_name": tradeline.tradeline_name,
                "bank": tradeline.bank,  # Bank from tradeline master
                "bank_name": tradeline.bank_name,  # Bank name from tradeline bank table
                "bank_logo": tradeline.bank_logo,  # Bank logo from tradeline bank table
                "credit_limit": tradeline.credit_limit,  # From tradeline master
                "age_year": tradeline.age_year,  # From tradeline master
                "age_month": tradeline.age_month,  # From tradeline master
                "closing_date": tradeline.closing_date,  # From tradeline master
                "quantity": tradeline.quantity,
                "unit_price": float(tradeline.unit_price) if tradeline.unit_price else 0.0,
                "total_amount": float(tradeline.total_amount) if tradeline.total_amount else 0.0,
                "notes": tradeline.notes,
                "expiry_date": tradeline.expiry_date,
                "assigned_to": tradeline.assigned_to,
                "completion_date": tradeline.completion_date,
                "creation": tradeline.creation,
                "modified": tradeline.modified,
                "commission_paid": tradeline.commission_paid,
                "commission": tradeline.commission,
                "refund_username": tradeline.refund_username,
                "refund_security_question": tradeline.refund_security_question,
                "refund_security_answer": tradeline.refund_security_answer,
                "refund_pin": tradeline.refund_pin,
                "refund_reason": tradeline.refund_reason,
                "refund_link": tradeline.refund_link,
                "swapped": tradeline.swapped,
                "swapped_on": tradeline.swapped_on
            }
            formatted_tradelines.append(formatted_tradeline)
        
        # Calculate pagination
        current_page = (int(start) // int(limit)) + 1 if int(limit) > 0 else 1
        total_pages = (total + int(limit) - 1) // int(limit) if int(limit) > 0 else 1
        has_next = (int(start) + int(limit)) < total
        has_previous = int(start) > 0
        
        return {
            "success": True,
            "data": formatted_tradelines,
            "pagination": {
                "current_page": current_page,
                "total_pages": total_pages,
                "limit": int(limit),
                "start": int(start),
                "has_next": has_next,
                "has_previous": has_previous,
                "total_records": total
            },
            "is_admin": is_admin,
            "user": current_user
        }

    except Exception as e:
        frappe.throw(f"Failed to fetch client tradelines: {str(e)}")

@frappe.whitelist(allow_guest=True)
@jwt_required()
def swap(client_tradeline, tradeline):
    return frappe.get_doc("Client Tradelines", client_tradeline).swap(tradeline)

@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_my_client_tradelines(status=None, limit=20, start=0):
    """Get current user's client tradelines only"""
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.throw(_("Authentication required"))

        is_admin = is_administrator(current_user)

        # Find customer record for current user
        customer_records = frappe.get_all("Customer", 
            filters= dict() if is_admin else { "email_id": current_user}, 
            fields=["name", "customer_name"])
       
        
        
        
        if not customer_records:
            return {
                "success": True,
                "data": [],
                "total": 0,
                "message": "No customer record found for current user"
            }
        
        # Build query conditions
        conditions = []
        values = []
        
        customer_names = [rec.name for rec in customer_records]
        customer_placeholders = ", ".join(["%s"] * len(customer_names))
        conditions.append(f"ct.customer IN ({customer_placeholders})")
        values.extend(customer_names)
        
        # Add status filter if provided
        if status:
            conditions.append("ct.status = %s")
            values.append(status)
        
        # Build WHERE clause
        where_clause = "WHERE " + " AND ".join(conditions)
        
        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total
            FROM `tabClient Tradelines` ct
            LEFT JOIN `tabTradeline` t ON ct.tradeline = t.name
            LEFT JOIN `tabTradeline Bank` tb ON t.bank = tb.name
            {where_clause}
        """
        
        total_result = frappe.db.sql(count_query, values, as_dict=True)
        total = total_result[0].total if total_result else 0
        
        # Get paginated results with tradeline details
        query = f"""
            SELECT 
                ct.name,
                ct.title,
                ct.customer,
                ct.customer_name,
                ct.status,
                ct.created_date,
                ct.cart,
                ct.payment_request,
                ct.tradeline,
                ct.tradeline_name,
                ct.quantity,
                ct.unit_price,
                ct.total_amount,
                ct.notes,
                ct.expiry_date,
                ct.assigned_to,
                ct.completion_date,
                ct.creation,
                ct.modified,
                ct.commission_paid,
                ct.refund_username,
                ct.refund_security_question,
                ct.refund_security_answer,
                ct.refund_pin,
                ct.refund_reason,
                ct.refund_link,
                ct.swapped,
                ct.swapped_on,
                t.bank,
                tb.bank_name,
                tb.image as bank_logo,
                t.credit_limit,
                t.age_year,
                t.age_month,
                t.closing_date
            FROM `tabClient Tradelines` ct
            LEFT JOIN `tabTradeline` t ON ct.tradeline = t.name
            LEFT JOIN `tabTradeline Bank` tb ON t.bank = tb.name
            {where_clause}
            ORDER BY ct.modified DESC
            LIMIT %s OFFSET %s
        """
        
        values.extend([int(limit), int(start)])
        
        tradelines = frappe.db.sql(query, values, as_dict=True)
        
        # Format the response
        formatted_tradelines = []
        for tradeline in tradelines:
            formatted_tradeline = {
                "id": tradeline.name,  # Client tradeline ID
                "title": tradeline.title,
                "customer": tradeline.customer,
                "customer_name": tradeline.customer_name,
                "status": tradeline.status,
                "purchase_date": tradeline.creation,  # Purchase date from creation
                "date_added": tradeline.completion_date,  # Date added
                "removal_date": tradeline.expiry_date,  # Removal date
                "cart_id": tradeline.cart,
                "payment_request_id": tradeline.payment_request,
                "tradeline": tradeline.tradeline,  # Tradeline reference ID
                "tradeline_name": tradeline.tradeline_name,
                "bank": tradeline.bank,  # Bank from tradeline master
                "bank_name": tradeline.bank_name,  # Bank name from tradeline bank table
                "bank_logo": tradeline.bank_logo,  # Bank logo from tradeline bank table
                "credit_limit": tradeline.credit_limit,  # From tradeline master
                "age_year": tradeline.age_year,  # From tradeline master
                "age_month": tradeline.age_month,  # From tradeline master
                "closing_date": tradeline.closing_date,  # From tradeline master
                "quantity": tradeline.quantity,
                "unit_price": float(tradeline.unit_price) if tradeline.unit_price else 0.0,
                "total_amount": float(tradeline.total_amount) if tradeline.total_amount else 0.0,
                "notes": tradeline.notes,
                "created_date": tradeline.created_date,
                "assigned_to": tradeline.assigned_to,
                "completion_date": tradeline.completion_date,
                "expiry_date": tradeline.expiry_date,
                "creation": tradeline.creation,
                "modified": tradeline.modified,
                "commission_paid": tradeline.commission_paid,
                "refund_username": tradeline.refund_username,
                "refund_security_question": tradeline.refund_security_question,
                "refund_security_answer": tradeline.refund_security_answer,
                "refund_pin": tradeline.refund_pin,
                "refund_reason": tradeline.refund_reason,
                "refund_link": tradeline.refund_link,
                "swapped": tradeline.swapped,
                "swapped_on": tradeline.swapped_on
            }
            formatted_tradelines.append(formatted_tradeline)
        
        # Calculate pagination
        current_page = (int(start) // int(limit)) + 1 if int(limit) > 0 else 1
        total_pages = (total + int(limit) - 1) // int(limit) if int(limit) > 0 else 1
        has_next = (int(start) + int(limit)) < total
        has_previous = int(start) > 0
        
        return {
            "success": True,
            "data": formatted_tradelines,
            "pagination": {
                "current_page": current_page,
                "total_pages": total_pages,
                "limit": int(limit),
                "start": int(start),
                "has_next": has_next,
                "has_previous": has_previous,
                "total_records": total
            },
            "user": current_user,
            "customer_records": [{"name": rec.name, "customer_name": rec.customer_name} for rec in customer_records]
        }

    except Exception as e:
        frappe.throw(f"Failed to fetch your client tradelines: {str(e)}")


@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_client_tradeline_details(tradeline_id):
    """Get detailed information about a specific client tradeline"""
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.throw(_("Authentication required"))

        # Check if user is administrator
        is_admin = is_administrator(current_user)
        
        # Get the tradeline document
        tradeline_doc = frappe.get_doc("Client Tradelines", tradeline_id)
        
        # Check permissions
        if not is_admin:
            # Find customer record for current user
            customer_records = frappe.get_all("Customer", 
                filters={"email_id": current_user}, 
                fields=["name"])
            
            if not customer_records:
                frappe.throw(_("No customer record found for current user"))
            
            customer_names = [rec.name for rec in customer_records]
            
            # Check if tradeline belongs to current user
            # if tradeline_doc.customer not in customer_names:
            #     frappe.throw(_("Access denied. You can only view your own tradelines."))
        
        # Get related documents
        cart_doc = None
        payment_request_doc = None
        tradeline_master = None
        customer_doc = None
        attachments = []
        
        try:
            if tradeline_doc.cart:
                cart_doc = frappe.get_doc("Tradeline Cart", tradeline_doc.cart)
        except:
            pass
        
        try:
            if tradeline_doc.payment_request:
                payment_request_doc = frappe.get_doc("Payment Request", tradeline_doc.payment_request)
        except:
            pass
        
        try:
            if tradeline_doc.tradeline:
                tradeline_master = frappe.get_doc("Tradeline", tradeline_doc.tradeline)
        except:
            pass
        
        try:
            if tradeline_doc.customer:
                customer_doc = frappe.get_doc("Customer", tradeline_doc.customer)
        except:
            pass
        
        # Get attachments for the Client Tradeline document
        try:
            attachments_query = """
                SELECT 
                    name,
                    file_name,
                    file_url,
                    file_size,
                    is_private,
                    creation,
                    modified,
                    owner
                FROM `tabFile`
                WHERE attached_to_doctype = %s AND attached_to_name = %s
                ORDER BY creation DESC
            """
            attachments_result = frappe.db.sql(attachments_query, ("Client Tradelines", tradeline_doc.name), as_dict=True)
            
            attachments = []
            for attachment in attachments_result:
                attachments.append({
                    "id": attachment.name,
                    "file_name": attachment.file_name,
                    "file_url": attachment.file_url,
                    "file_size": attachment.file_size,
                    "is_private": attachment.is_private,
                    "uploaded_by": attachment.owner,
                    "upload_date": attachment.creation,
                    "modified": attachment.modified
                })
        except Exception as e:
            frappe.log_error(f"Error fetching attachments for Client Tradeline {tradeline_doc.name}: {str(e)}")
            attachments = []

        customer_info = customer_doc.as_dict() if customer_doc else None
        if customer_info:
        # Add date of birth from linked User record
            user_doc = frappe.get_doc("User", customer_info.get("email_id"))
            customer_info["date_of_birth"] = user_doc.get("birth_date") if user_doc else None
            # Hide tax_id field from customer response if tradeline_master does not require ssn
            if tradeline_master and not tradeline_master.get("requires_ssn"):
                customer_info["tax_id"] = None
            if tradeline_master and tradeline_master.get("requires_address"):
                customer_info["customer_address_details"] = {}
         
                addresses = frappe.get_all("Address", filters={"email_id": customer_info.get("email_id")}, fields=["name", "address_line1", "address_line2", "city", "state", "pincode", "country"])
                if addresses and len(addresses) > 0:
                    customer_info["customer_address_details"] = addresses[0]
         
        # Format the response
        response = {
            "success": True,
            "tradeline": {
                "id": tradeline_doc.name,
                "title": tradeline_doc.title,
                "customer": tradeline_doc.customer,
                "customer_name": tradeline_doc.customer_name,
                "status": tradeline_doc.status,
                "created_date": tradeline_doc.created_date,
                "cart_id": tradeline_doc.cart,
                "payment_request_id": tradeline_doc.payment_request,
                "tradeline": tradeline_doc.tradeline,
                "tradeline_name": tradeline_doc.tradeline_name,
                "quantity": tradeline_doc.quantity,
                "unit_price": float(tradeline_doc.unit_price) if tradeline_doc.unit_price else 0.0,
                "total_amount": float(tradeline_doc.total_amount) if tradeline_doc.total_amount else 0.0,
                "notes": tradeline_doc.notes,
                "expiry_date": tradeline_doc.expiry_date,
                "assigned_to": tradeline_doc.assigned_to,
                "completion_date": tradeline_doc.completion_date,
                "creation": tradeline_doc.creation,
                "modified": tradeline_doc.modified,
                "commission_paid": tradeline_doc.commission_paid,
                "refund_username": getattr(tradeline_doc, 'refund_username', None),
                "refund_security_question": getattr(tradeline_doc, 'refund_security_question', None),
                "refund_security_answer": getattr(tradeline_doc, 'refund_security_answer', None),
                "refund_pin": getattr(tradeline_doc, 'refund_pin', None),
                "refund_reason": getattr(tradeline_doc, 'refund_reason', None),
                "refund_link": getattr(tradeline_doc, 'refund_link', None),
                "swapped": getattr(tradeline_doc, 'swapped', None),
                "swapped_on": getattr(tradeline_doc, 'swapped_on', None)
            },
            "attachments": attachments,
            "related_documents": {
                "cart": cart_doc.as_dict() if cart_doc else None,
                "payment_request": payment_request_doc.as_dict() if payment_request_doc else None,
                "tradeline_master": tradeline_master.as_dict() if tradeline_master else None,
                "customer": customer_info
            },
            "user": current_user,
            "is_admin": is_admin
        }
        
        return response

    except Exception as e:
        frappe.throw(f"Failed to fetch client tradeline details: {str(e)}")


@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_client_tradeline_attachments(tradeline_id):
    """Get all attachments for a specific client tradeline"""
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.throw(_("Authentication required"))

        # Check if user is administrator
        is_admin = is_administrator(current_user)
        
        # Get the tradeline document to verify access
        tradeline_doc = frappe.get_doc("Client Tradelines", tradeline_id)
        
        # Check permissions
        if not is_admin:
            # Find customer record for current user
            customer_records = frappe.get_all("Customer", 
                filters={"email_id": current_user}, 
                fields=["name"])
            
            if not customer_records:
                frappe.throw(_("No customer record found for current user"))
            
            customer_names = [rec.name for rec in customer_records]
            
            # Check if tradeline belongs to current user
            if tradeline_doc.customer not in customer_names:
                frappe.throw(_("Access denied. You can only view attachments for your own tradelines."))
        
        # Get attachments for the Client Tradeline document
        attachments_query = """
            SELECT 
                name,
                file_name,
                file_url,
                file_size,
                is_private,
                creation,
                modified,
                owner
            FROM `tabFile`
            WHERE attached_to_doctype = %s AND attached_to_name = %s
            ORDER BY creation DESC
        """
        attachments_result = frappe.db.sql(attachments_query, ("Client Tradelines", tradeline_id), as_dict=True)
        
        attachments = []
        for attachment in attachments_result:
            attachments.append({
                "id": attachment.name,
                "file_name": attachment.file_name,
                "file_url": attachment.file_url,
                "file_size": attachment.file_size,
                "is_private": attachment.is_private,
                "uploaded_by": attachment.owner,
                "upload_date": attachment.creation,
                "modified": attachment.modified,
                "download_url": f"/api/method/frappe.utils.file_manager.download_file?fid={attachment.name}"
            })
        
        return {
            "success": True,
            "tradeline_id": tradeline_id,
            "attachments": attachments,
            "total_attachments": len(attachments),
            "user": current_user,
            "is_admin": is_admin
        }

    except Exception as e:
        frappe.throw(f"Failed to fetch client tradeline attachments: {str(e)}")


@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_client_tradeline_statistics(customer=None):
    """Get statistics about client tradelines"""
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.throw(_("Authentication required"))

        # Check if user is administrator
        is_admin = is_administrator(current_user)
        
        # Build base query conditions
        conditions = []
        values = []
        
        # If not admin, filter by customer email
        if not is_admin:
            # Find customer record for current user
            customer_records = frappe.get_all("Customer", 
                filters={"email_id": current_user}, 
                fields=["name"])
            
            if not customer_records:
                return {
                    "success": True,
                    "statistics": {
                        "total_tradelines": 0,
                        "active_tradelines": 0,
                        "completed_tradelines": 0,
                        "expired_tradelines": 0,
                        "cancelled_tradelines": 0,
                        "total_amount": 0.0,
                        "average_amount": 0.0
                    },
                    "message": "No customer record found for current user"
                }
            
            customer_names = [rec.name for rec in customer_records]
            customer_placeholders = ", ".join(["%s"] * len(customer_names))
            conditions.append(f"customer IN ({customer_placeholders})")
            values.extend(customer_names)
        else:
            # Admin can optionally filter by specific customer
            if customer:
                conditions.append("customer = %s")
                values.append(customer)
        
        # Build WHERE clause
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
        
        # Get overall statistics
        stats_query = f"""
            SELECT 
                COUNT(*) as total_tradelines,
                SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END) as active_tradelines,
                SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed_tradelines,
                SUM(CASE WHEN status = 'Expired' THEN 1 ELSE 0 END) as expired_tradelines,
                SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END) as cancelled_tradelines,
                SUM(CASE WHEN status = 'Inactive' THEN 1 ELSE 0 END) as inactive_tradelines,
                SUM(total_amount) as total_amount,
                AVG(total_amount) as average_amount
            FROM `tabClient Tradelines`
            {where_clause}
        """
        
        stats_result = frappe.db.sql(stats_query, values, as_dict=True)
        stats = stats_result[0] if stats_result else {}
        
        # Get status breakdown
        status_query = f"""
            SELECT 
                status,
                COUNT(*) as count,
                SUM(total_amount) as amount
            FROM `tabClient Tradelines`
            {where_clause}
            GROUP BY status
        """
        
        status_breakdown = frappe.db.sql(status_query, values, as_dict=True)
        
        # Get recent activity (last 30 days)
        recent_conditions = conditions.copy()
        recent_values = values.copy()
        recent_conditions.append("created_date >= %s")
        recent_values.append((now_datetime().date() - frappe.utils.datetime.timedelta(days=30)).strftime('%Y-%m-%d'))
        
        recent_where_clause = "WHERE " + " AND ".join(recent_conditions)
        
        recent_query = f"""
            SELECT COUNT(*) as recent_count
            FROM `tabClient Tradelines`
            {recent_where_clause}
        """
        
        recent_result = frappe.db.sql(recent_query, recent_values, as_dict=True)
        recent_count = recent_result[0].recent_count if recent_result else 0
        
        return {
            "success": True,
            "statistics": {
                "total_tradelines": stats.get("total_tradelines", 0),
                "active_tradelines": stats.get("active_tradelines", 0),
                "completed_tradelines": stats.get("completed_tradelines", 0),
                "expired_tradelines": stats.get("expired_tradelines", 0),
                "cancelled_tradelines": stats.get("cancelled_tradelines", 0),
                "inactive_tradelines": stats.get("inactive_tradelines", 0),
                "total_amount": float(stats.get("total_amount", 0) or 0),
                "average_amount": float(stats.get("average_amount", 0) or 0),
                "recent_activity_30_days": recent_count
            },
            "status_breakdown": [
                {
                    "status": item.status,
                    "count": item.count,
                    "amount": float(item.amount or 0)
                }
                for item in status_breakdown
            ],
            "user": current_user,
            "is_admin": is_admin
        }

    except Exception as e:
        frappe.throw(f"Failed to fetch client tradeline statistics: {str(e)}")


@frappe.whitelist(allow_guest=True)
@jwt_required()
def update_client_tradeline_status(tradeline_id, new_status=None, notes=None, commission_paid=None, 
                                 refund_username=None, refund_password=None, refund_security_question=None, 
                                 refund_security_answer=None, refund_pin=None, refund_reason=None, refund_link=None):
    """Update client tradeline status (Admin only or assigned user)"""
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.throw(_("Authentication required"))

        # Check if user is administrator
        is_admin = is_administrator(current_user)
        
        # Get the tradeline document
        tradeline_doc = frappe.get_doc("Client Tradelines", tradeline_id)
        
        # Update commission_paid if provided and user is admin
        if is_admin and commission_paid is not None:
            tradeline_doc.commission_paid = commission_paid
        
        # Check permissions
        # if not is_admin and tradeline_doc.assigned_to != current_user:
        #     frappe.throw(_("Access denied. Only administrators or assigned users can update tradeline status."))
        
        # If new_status is "Refund Requested", validate required refund fields
        if new_status == "Refund Requested":
            required_refund_fields = {
                "refund_username": refund_username,
                "refund_password": refund_password,
                "refund_security_question": refund_security_question,
                "refund_security_answer": refund_security_answer,
                "refund_pin": refund_pin,
                "refund_reason": refund_reason,
                "refund_link": refund_link
            }
            
            missing_fields = []
            for field_name, field_value in required_refund_fields.items():
                if not field_value or str(field_value).strip() == "":
                    missing_fields.append(field_name.replace("_", " ").title())
            
            if missing_fields:
                frappe.throw(_(f"The following refund fields are required when status is 'Refund Requested': {', '.join(missing_fields)}"))
            
            # Set refund fields
            tradeline_doc.refund_username = refund_username
            tradeline_doc.refund_password = refund_password
            tradeline_doc.refund_security_question = refund_security_question
            tradeline_doc.refund_security_answer = refund_security_answer
            tradeline_doc.refund_pin = refund_pin
            tradeline_doc.refund_reason = refund_reason
            tradeline_doc.refund_link = refund_link
        
        # Validate new status
        valid_statuses = ["Active", "Inactive", "Completed", "Expired", "Cancelled", "Refunded", "Refund Requested"]
        if new_status and new_status not in valid_statuses:
            frappe.throw(_(f"Invalid status. Valid options are: {', '.join(valid_statuses)}"))
        
        # Update the document
        old_status = tradeline_doc.status
        if new_status:
            tradeline_doc.status = new_status
        
        # Add notes if provided
        if notes:
            existing_notes = tradeline_doc.notes or ""
            timestamp = now_datetime().strftime("%Y-%m-%d %H:%M:%S")
            new_note = f"\n[{timestamp}] Status changed from '{old_status}' to '{new_status}' by {current_user}: {notes}"
            tradeline_doc.notes = existing_notes + new_note
        
        # Set completion date if status is completed
        if new_status == "Completed" and not tradeline_doc.completion_date:
            tradeline_doc.completion_date = getdate()
        
        tradeline_doc.save(ignore_permissions=True)
        frappe.db.commit()
        
        response = {
            "success": True,
            "message": f"Tradeline status updated from '{old_status}' to '{new_status}'" if new_status else "Tradeline updated successfully",
            "tradeline_id": tradeline_id,
            "old_status": old_status,
            "new_status": new_status,
            "updated_by": current_user,
            "updated_at": now_datetime()
        }
        
        # Include refund fields in response if they were provided
        if new_status == "Refund Requested":
            response["refund_details"] = {
                "refund_username": refund_username,
                "refund_security_question": refund_security_question,
                "refund_pin": refund_pin,
                "refund_reason": refund_reason,
                "refund_link": refund_link
                # Note: We don't return password and security answer for security reasons
            }
        
        return response

    except Exception as e:
        frappe.throw(f"Failed to update client tradeline status: {str(e)}")


@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_client_tradelines_for_sellers(status=None, limit=20, start=0):
    """Get client tradelines for the current user as cardholder/seller"""
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.throw(_("Authentication required"))

        # Check if user is administrator
        is_admin = is_administrator(current_user)
        
        # Build base query conditions
        conditions = []
        values = []
        
        # If not admin, filter by card holder email matching current user
        if not is_admin:
            conditions.append("ch.email_id = %s")
            values.append(current_user)
        
        # Add status filter if provided
        if status:
            conditions.append("ct.status = %s")
            values.append(status)
        
        # Build WHERE clause
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
        
        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total
            FROM `tabClient Tradelines` ct
            LEFT JOIN `tabTradeline` t ON ct.tradeline = t.name
            LEFT JOIN `tabCustomer` ch ON t.card_holder = ch.name
            {where_clause}
        """
        
        total_result = frappe.db.sql(count_query, values, as_dict=True)
        total = total_result[0].total if total_result else 0
        
        # Get paginated results with tradeline and cardholder details
        query = f"""
            SELECT 
                ct.name,
                ct.title,
                ct.customer,
                ct.customer_name,
                ct.status,
                ct.created_date,
                ct.cart,
                ct.payment_request,
                ct.tradeline,
                ct.tradeline_name,
                ct.quantity,
                ct.unit_price,
                ct.total_amount,
                ct.notes,
                ct.expiry_date,
                ct.assigned_to,
                ct.completion_date,
                ct.creation,
                ct.modified,
                ct.commission_paid,
                ct.refund_username,
                ct.refund_security_question,
                ct.refund_security_answer,
                ct.refund_pin,
                ct.refund_reason,
                ct.refund_link,
                ct.swapped,
                ct.swapped_on,
                t.bank,
                tb.bank_name,
                tb.image as bank_logo,
                t.credit_limit,
                t.age_year,
                t.age_month,
                t.closing_date,
                t.credit_utilization_rate,
                ch.name as card_holder_id,
                ch.customer_name as card_holder_name,
                ch.email_id as card_holder_email
            
            FROM `tabClient Tradelines` ct
            LEFT JOIN `tabTradeline` t ON ct.tradeline = t.name
            LEFT JOIN `tabTradeline Bank` tb ON t.bank = tb.name
            LEFT JOIN `tabCustomer` ch ON t.card_holder = ch.name
            {where_clause}
            ORDER BY ct.modified DESC
            LIMIT %s OFFSET %s
        """
        
        values.extend([int(limit), int(start)])
        
        tradelines = frappe.db.sql(query, values, as_dict=True)
        
        # Format the response
        formatted_tradelines = []
        for tradeline in tradelines:
            formatted_tradeline = {
                "id": tradeline.name,  # Client tradeline ID
                "title": tradeline.title,
                "customer": tradeline.customer,
                "customer_name": tradeline.customer_name,
                "status": tradeline.status,
                "created_date": tradeline.created_date,
                "cart_id": tradeline.cart,
                "payment_request_id": tradeline.payment_request,
                "tradeline": tradeline.tradeline,  # Tradeline reference ID
                "tradeline_name": tradeline.tradeline_name,
                "quantity": tradeline.quantity,
                "unit_price": float(tradeline.unit_price) if tradeline.unit_price else 0.0,
                "total_amount": float(tradeline.total_amount) if tradeline.total_amount else 0.0,
                "notes": tradeline.notes,
                "expiry_date": tradeline.expiry_date,
                "assigned_to": tradeline.assigned_to,
                "completion_date": tradeline.completion_date,
                "creation": tradeline.creation,
                "modified": tradeline.modified,
                "commission_paid": tradeline.commission_paid,
                "refund_username": tradeline.refund_username,
                "refund_security_question": tradeline.refund_security_question,
                "refund_security_answer": tradeline.refund_security_answer,
                "refund_pin": tradeline.refund_pin,
                "refund_reason": tradeline.refund_reason,
                "swapped": tradeline.swapped,
                "swapped_on": tradeline.swapped_on,
                # Tradeline details
                "bank": tradeline.bank,
                "bank_name": tradeline.bank_name,
                "bank_logo": tradeline.bank_logo,
                "credit_limit": tradeline.credit_limit,
                "age_year": tradeline.age_year,
                "age_month": tradeline.age_month,
                "closing_date": tradeline.closing_date,
                "credit_utilization_rate": tradeline.credit_utilization_rate,
                # Card holder details
                "card_holder": {
                    "id": tradeline.card_holder_id,
                    "name": tradeline.card_holder_name,
                    "email": tradeline.card_holder_email,
                    "phone": tradeline.card_holder_phone
                }
            }
            formatted_tradelines.append(formatted_tradeline)
        
        # Calculate pagination
        current_page = (int(start) // int(limit)) + 1 if int(limit) > 0 else 1
        total_pages = (total + int(limit) - 1) // int(limit) if int(limit) > 0 else 1
        has_next = (int(start) + int(limit)) < total
        has_previous = int(start) > 0
        
        return {
            "success": True,
            "data": formatted_tradelines,
            "pagination": {
                "current_page": current_page,
                "total_pages": total_pages,
                "limit": int(limit),
                "start": int(start),
                "has_next": has_next,
                "has_previous": has_previous,
                "total_records": total
            },
            "is_admin": is_admin,
            "user": current_user,
            "message": "Client tradelines for cardholder/seller retrieved successfully"
        }

    except Exception as e:
        frappe.throw(f"Failed to fetch client tradelines for cardholder: {str(e)}")


@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_cardholder_tradeline_statistics():
    """Get statistics about client tradelines for current cardholder/seller"""
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.throw(_("Authentication required"))

        # Check if user is administrator
        is_admin = is_administrator(current_user)
        
        # Build base query conditions
        conditions = []
        values = []
        
        # If not admin, filter by card holder email matching current user
        if not is_admin:
            conditions.append("ch.email = %s")
            values.append(current_user)
        
        # Build WHERE clause
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
        
        # Get overall statistics
        stats_query = f"""
            SELECT 
                COUNT(*) as total_tradelines,
                SUM(CASE WHEN ct.status = 'Active' THEN 1 ELSE 0 END) as active_tradelines,
                SUM(CASE WHEN ct.status = 'Completed' THEN 1 ELSE 0 END) as completed_tradelines,
                SUM(CASE WHEN ct.status = 'Expired' THEN 1 ELSE 0 END) as expired_tradelines,
                SUM(CASE WHEN ct.status = 'Cancelled' THEN 1 ELSE 0 END) as cancelled_tradelines,
                SUM(CASE WHEN ct.status = 'Inactive' THEN 1 ELSE 0 END) as inactive_tradelines,
                SUM(ct.total_amount) as total_amount,
                AVG(ct.total_amount) as average_amount
            FROM `tabClient Tradelines` ct
            LEFT JOIN `tabTradeline` t ON ct.tradeline = t.name
            LEFT JOIN `tabCard Holder` ch ON t.card_holder = ch.name
            {where_clause}
        """
        
        stats_result = frappe.db.sql(stats_query, values, as_dict=True)
        stats = stats_result[0] if stats_result else {}
        
        # Get status breakdown
        status_query = f"""
            SELECT 
                ct.status,
                COUNT(*) as count,
                SUM(ct.total_amount) as amount
            FROM `tabClient Tradelines` ct
            LEFT JOIN `tabTradeline` t ON ct.tradeline = t.name
            LEFT JOIN `tabCard Holder` ch ON t.card_holder = ch.name
            {where_clause}
            GROUP BY ct.status
        """
        
        status_breakdown = frappe.db.sql(status_query, values, as_dict=True)
        
        # Get recent activity (last 30 days)
        recent_conditions = conditions.copy()
        recent_values = values.copy()
        recent_conditions.append("ct.created_date >= %s")
        recent_values.append((now_datetime().date() - frappe.utils.datetime.timedelta(days=30)).strftime('%Y-%m-%d'))
        
        recent_where_clause = "WHERE " + " AND ".join(recent_conditions)
        
        recent_query = f"""
            SELECT COUNT(*) as recent_count
            FROM `tabClient Tradelines` ct
            LEFT JOIN `tabTradeline` t ON ct.tradeline = t.name
            LEFT JOIN `tabCard Holder` ch ON t.card_holder = ch.name
            {recent_where_clause}
        """
        
        recent_result = frappe.db.sql(recent_query, recent_values, as_dict=True)
        recent_count = recent_result[0].recent_count if recent_result else 0
        
        return {
            "success": True,
            "statistics": {
                "total_tradelines": stats.get("total_tradelines", 0),
                "active_tradelines": stats.get("active_tradelines", 0),
                "completed_tradelines": stats.get("completed_tradelines", 0),
                "expired_tradelines": stats.get("expired_tradelines", 0),
                "cancelled_tradelines": stats.get("cancelled_tradelines", 0),
                "inactive_tradelines": stats.get("inactive_tradelines", 0),
                "total_amount": float(stats.get("total_amount", 0) or 0),
                "average_amount": float(stats.get("average_amount", 0) or 0),
                "recent_activity_30_days": recent_count
            },
            "status_breakdown": [
                {
                    "status": item.status,
                    "count": item.count,
                    "amount": float(item.amount or 0)
                }
                for item in status_breakdown
            ],
            "user": current_user,
            "is_admin": is_admin
        }

    except Exception as e:
        frappe.throw(f"Failed to fetch cardholder tradeline statistics: {str(e)}")


@frappe.whitelist(allow_guest=True)
@jwt_required()
def request_refund(client_tradeline_name, refund_reason=None):
    """
    Request refund for a client tradeline
    
    Args:
        client_tradeline_name (str): The name/ID of the Client Tradeline document
        refund_reason (str, optional): Reason for requesting refund
        
    Returns:
        dict: Success/failure response
    """
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.throw(_("Authentication required"))

        # Check if user is administrator
        is_admin = is_administrator(current_user)
        
        # Get the client tradeline document
        try:
            client_tradeline_doc = frappe.get_doc("Client Tradelines", client_tradeline_name)
        except frappe.DoesNotExistError:
            return {
                "success": False,
                "message": "Client tradeline not found"
            }
        
        # Check permissions - validate it belongs to the logged-in user or user is admin
        if not is_admin:
            # Find customer record for current user
            customer_records = frappe.get_all("Customer", 
                filters={"email_id": current_user}, 
                fields=["name"])
            
            if not customer_records:
                frappe.throw(_("No customer record found for current user"))
            
            customer_names = [rec.name for rec in customer_records]
            
            # Check if tradeline belongs to current user
            if client_tradeline_doc.customer not in customer_names:
                return {
                    "success": False,
                    "message": "Access denied. You can only request refunds for your own tradelines."
                }
        
        # Check if refund can be requested (status validation)
        current_status = client_tradeline_doc.status
        refundable_statuses = ["Active", "Completed", "Expired"]
        
        if current_status not in refundable_statuses:
            return {
                "success": False,
                "message": f"Cannot request refund for tradeline with status '{current_status}'. Only tradelines with status 'Active', 'Completed', or 'Expired' can be refunded."
            }
        
        # Check if refund was already requested
        if current_status == "Refund Requested":
            return {
                "success": False,
                "message": "Refund has already been requested for this tradeline."
            }
        
        # Update status to "Refund Requested"
        old_status = client_tradeline_doc.status
        client_tradeline_doc.status = "Refund Requested"
        
        # Add refund reason to notes
        timestamp = now_datetime().strftime("%Y-%m-%d %H:%M:%S")
        refund_note = f"\n[{timestamp}] Refund requested by {current_user}"
        if refund_reason:
            refund_note += f" - Reason: {refund_reason}"
        
        existing_notes = client_tradeline_doc.notes or ""
        client_tradeline_doc.notes = existing_notes + refund_note
        
        # Save the document
        client_tradeline_doc.save(ignore_permissions=True)
        frappe.db.commit()
        
        # Send email notification to admin
        send_refund_request_notification(client_tradeline_doc, current_user, refund_reason)
        
        return {
            "success": True,
            "message": "Refund request submitted successfully. Our team will review your request and get back to you shortly.",
            "client_tradeline_id": client_tradeline_name,
            "old_status": old_status,
            "new_status": "Refund Requested",
            "requested_by": current_user,
            "request_date": now_datetime(),
            "refund_reason": refund_reason
        }
        
    except Exception as e:
        frappe.log_error(f"Refund request failed: {str(e)}", "Refund Request Error")
        return {
            "success": False,
            "message": f"An error occurred while processing your refund request: {str(e)}"
        }


def send_refund_request_notification(client_tradeline_doc, requesting_user, refund_reason=None):
    """
    Send email notification to admin about refund request
    
    Args:
        client_tradeline_doc: Client Tradeline document
        requesting_user (str): Email of user requesting refund
        refund_reason (str, optional): Reason for refund
    """
    try:
        # Get related information
        customer_doc = None
        tradeline_doc = None
        payment_request_doc = None
        
        try:
            if client_tradeline_doc.customer:
                customer_doc = frappe.get_doc("Customer", client_tradeline_doc.customer)
        except:
            pass
        
        try:
            if client_tradeline_doc.tradeline:
                tradeline_doc = frappe.get_doc("Tradeline", client_tradeline_doc.tradeline)
        except:
            pass
        
        try:
            if client_tradeline_doc.payment_request:
                payment_request_doc = frappe.get_doc("Payment Request", client_tradeline_doc.payment_request)
        except:
            pass
        
        # Get bank information
        bank_name = "Unknown Bank"
        if tradeline_doc and tradeline_doc.bank:
            try:
                bank_doc = frappe.get_doc("Tradeline Bank", tradeline_doc.bank)
                bank_name = bank_doc.bank_name
            except:
                pass
        
        # Prepare template parameters
        template_params = {
            "client_tradeline_id": client_tradeline_doc.name,
            "request_date": now_datetime().strftime('%Y-%m-%d %H:%M:%S'),
            "requesting_user": requesting_user,
            "previous_status": client_tradeline_doc.get_doc_before_save().status if client_tradeline_doc.get_doc_before_save() else 'N/A',
            "refund_reason": refund_reason or 'No reason provided',
            "customer_id": client_tradeline_doc.customer,
            "customer_name": client_tradeline_doc.customer_name,
            "customer_email": customer_doc.email_id if customer_doc else 'N/A',
            "customer_phone": customer_doc.mobile_no if customer_doc else 'N/A',
            "tradeline_id": client_tradeline_doc.tradeline or 'N/A',
            "tradeline_name": client_tradeline_doc.tradeline_name or 'N/A',
            "bank_name": bank_name,
            "credit_limit": f"{tradeline_doc.credit_limit:,}" if tradeline_doc and tradeline_doc.credit_limit else 'N/A',
            "tradeline_age": f"{tradeline_doc.age_year} years {tradeline_doc.age_month or 0} months" if tradeline_doc else 'N/A',
            "quantity": client_tradeline_doc.quantity,
            "unit_price": f"{client_tradeline_doc.unit_price:.2f}",
            "total_amount": f"{client_tradeline_doc.total_amount:.2f}",
            "payment_request_id": client_tradeline_doc.payment_request or 'N/A',
            "cart_id": client_tradeline_doc.cart or 'N/A',
            "purchase_date": str(client_tradeline_doc.creation),
            "completion_date": client_tradeline_doc.completion_date or 'N/A',
            "expiry_date": client_tradeline_doc.expiry_date or 'N/A',
            "last_modified": str(client_tradeline_doc.modified)
        }
        
        # Send email using template
        send_email_template(
            template_name="Refund Request Notification",
            recipients=["info@rockettradeline.com"],
            parameters=template_params
        )
        
        # Log the notification
        frappe.logger().info(f"Refund request notification sent to admin for client tradeline {client_tradeline_doc.name}")
        
    except Exception as e:
        frappe.log_error(f"Failed to send refund request notification: {str(e)}", "Refund Request Email Error")

@frappe.whitelist(allow_guest=True)
@jwt_required()
def apply_discount(client_tradeline_id, discount_type, discount_value):
    """
    Apply a discount to a Client Tradeline
    
    Args:
        client_tradeline_id: Name of the Client Tradeline document
        discount_type: Either "Percentage" or "Amount"
        discount_value: The discount value (percentage or fixed amount)
    
    Returns:
        dict: Updated client tradeline details with discount applied
    
    Raises:
        frappe.ValidationError: If validation fails
    """
    try:
        # Validate inputs
        if not client_tradeline_id:
            frappe.throw("Client Tradeline ID is required")
        
        if not discount_type or discount_type not in ["Percentage", "Amount"]:
            frappe.throw("Discount type must be either 'Percentage' or 'Amount'")
        
        if not discount_value:
            frappe.throw("Discount value is required")
        
        # Convert discount_value to float
        try:
            discount_value = flt(discount_value)
        except:
            frappe.throw("Discount value must be a valid number")
        
        if discount_value < 0:
            frappe.throw("Discount value cannot be negative")
        
        # Get the client tradeline document
        client_tradeline = frappe.get_doc("Client Tradelines", client_tradeline_id)
        
        # Check permissions
        if not frappe.has_permission("Client Tradelines", "write", client_tradeline):
            frappe.throw("You don't have permission to modify this Client Tradeline")
        
        # Apply the discount
        client_tradeline.discount_type = discount_type
        client_tradeline.discount_value = discount_value
        
        # Save the document (this will trigger validation and calculation)
        client_tradeline.save()
        
        frappe.db.commit()
        
        return {
            "success": True,
            "message": "Discount applied successfully",
            "client_tradeline": {
                "name": client_tradeline.name,
                "customer": client_tradeline.customer,
                "customer_name": client_tradeline.customer_name,
                "tradeline": client_tradeline.tradeline,
                "tradeline_name": client_tradeline.tradeline_name,
                "quantity": client_tradeline.quantity,
                "unit_price": client_tradeline.unit_price,
                "subtotal": client_tradeline.subtotal,
                "discount_type": client_tradeline.discount_type,
                "discount_value": client_tradeline.discount_value,
                "discount_amount": client_tradeline.discount_amount,
                "total_amount": client_tradeline.total_amount,
                "status": client_tradeline.status
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Failed to apply discount: {str(e)}", "Apply Discount Error")
        frappe.throw(f"Failed to apply discount: {str(e)}")


@frappe.whitelist(allow_guest=True)
@jwt_required()
def remove_discount(client_tradeline_id):
    """
    Remove discount from a Client Tradeline
    
    Args:
        client_tradeline_id: Name of the Client Tradeline document
    
    Returns:
        dict: Updated client tradeline details without discount
    
    Raises:
        frappe.ValidationError: If validation fails
    """
    try:
        # Validate input
        if not client_tradeline_id:
            frappe.throw("Client Tradeline ID is required")
        
        # Get the client tradeline document
        client_tradeline = frappe.get_doc("Client Tradelines", client_tradeline_id)
        
        # Check permissions
        if not frappe.has_permission("Client Tradelines", "write", client_tradeline):
            frappe.throw("You don't have permission to modify this Client Tradeline")
        
        # Remove the discount
        client_tradeline.discount_type = None
        client_tradeline.discount_value = 0
        client_tradeline.discount_amount = 0
        
        # Save the document (this will trigger recalculation)
        client_tradeline.save()
        
        frappe.db.commit()
        
        return {
            "success": True,
            "message": "Discount removed successfully",
            "client_tradeline": {
                "name": client_tradeline.name,
                "customer": client_tradeline.customer,
                "customer_name": client_tradeline.customer_name,
                "tradeline": client_tradeline.tradeline,
                "tradeline_name": client_tradeline.tradeline_name,
                "quantity": client_tradeline.quantity,
                "unit_price": client_tradeline.unit_price,
                "subtotal": client_tradeline.subtotal,
                "discount_type": client_tradeline.discount_type,
                "discount_value": client_tradeline.discount_value,
                "discount_amount": client_tradeline.discount_amount,
                "total_amount": client_tradeline.total_amount,
                "status": client_tradeline.status
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Failed to remove discount: {str(e)}", "Remove Discount Error")
        frappe.throw(f"Failed to remove discount: {str(e)}")

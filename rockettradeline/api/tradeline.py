from rockettradeline.api.auth import jwt_required, get_current_user,is_administrator, get_authenticated_user
import frappe
from frappe import _
import json


@frappe.whitelist(allow_guest=True)
@jwt_required()
def recalculate_tradeline_spots(tradeline_id=None):
    """
    Recalculate remaining spots for one or all tradelines
    Admin only endpoint
    """
    try:
        current_user = get_authenticated_user()
        if not is_administrator(current_user):
            return {
                "success": False,
                "error": "Only administrators can recalculate tradeline spots"
            }
        
        from rockettradeline.utils.tradeline_spots import (
            recalculate_tradeline_remaining_spots,
            recalculate_all_tradelines
        )
        
        if tradeline_id:
            # Recalculate single tradeline
            result = recalculate_tradeline_remaining_spots(tradeline_id)
            return result
        else:
            # Recalculate all tradelines
            result = recalculate_all_tradelines()
            return result
            
    except Exception as e:
        frappe.log_error(f"Error in recalculate_tradeline_spots API: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


# Tradeline APIs

@frappe.whitelist(allow_guest=True)
def get_tradelines(limit=20, start=0, search=None, filters=None):
    """
    Get list of tradelines
    """
    try:
        query_filters = {"status": "Active"}
        
        # Convert limit and start to integers
        limit = int(limit) if limit else 20
        start = int(start) if start else 0
        
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

        # Handle search across multiple fields
        if search:
            search_term = f"%{search}%"
            # Use SQL query for multi-field search
            search_conditions = """(
                t.name LIKE %(search)s OR
                t.bank LIKE %(search)s OR
                t.status LIKE %(search)s OR
                t.closing_date LIKE %(search)s OR
                CAST(t.credit_limit AS CHAR) LIKE %(search)s OR
                CAST(t.price AS CHAR) LIKE %(search)s OR
                CAST(t.age_year AS CHAR) LIKE %(search)s
            )"""
            
            # Build WHERE clause for filters
            where_conditions = ["t.status = 'Active'"]
            sql_values = {"search": search_term}
            
            if filters:
                if filters.get("min_price"):
                    where_conditions.append("t.price >= %(min_price)s")
                    sql_values["min_price"] = filters.get("min_price")
                if filters.get("max_price"):
                    where_conditions.append("t.price <= %(max_price)s")
                    sql_values["max_price"] = filters.get("max_price")
                if filters.get("min_credit_limit"):
                    where_conditions.append("t.credit_limit >= %(min_credit_limit)s")
                    sql_values["min_credit_limit"] = filters.get("min_credit_limit")
                if filters.get("bank"):
                    where_conditions.append("t.bank = %(bank)s")
                    sql_values["bank"] = filters.get("bank")
            
            where_conditions.append(search_conditions)
            where_clause = " AND ".join(where_conditions)
            
            # Get total count
            count_query = f"""SELECT COUNT(*) as count FROM `tabTradeline` t WHERE {where_clause}"""
            total_count = frappe.db.sql(count_query, sql_values, as_dict=True)[0].count
            
            # Get tradelines
            sql_values["limit"] = limit
            sql_values["start"] = start
            tradelines_query = f"""SELECT 
                t.name, t.bank, t.age_year, t.age_month, t.credit_limit,
                t.price, t.max_spots, t.remaining_spots, t.closing_date,
                t.credit_utilization_rate, t.status
                FROM `tabTradeline` t
                WHERE {where_clause}
                ORDER BY t.creation DESC
                LIMIT %(limit)s OFFSET %(start)s"""
            tradelines = frappe.db.sql(tradelines_query, sql_values, as_dict=True)
        else:
            # Get total count for pagination
            total_count = frappe.db.count("Tradeline", filters=query_filters)

            tradelines = frappe.get_all("Tradeline",
                filters=query_filters,
                fields=["name", "bank", "age_year", "age_month", "credit_limit", 
                       "price", "max_spots", "remaining_spots", "closing_date", 
                       "credit_utilization_rate", "status", "balance", "commission", 
                       "credit_usage", "late_payment"],
                limit=limit,
                start=start,
                order_by="creation desc"
            )
        
        # Get bank names
        for tradeline in tradelines:
            if tradeline.bank:
                bank_doc = frappe.get_doc("Tradeline Bank", tradeline.bank)
                tradeline.bank_name = bank_doc.bank_name
        
        # Calculate pagination
        current_page = (start // limit) + 1 if limit > 0 else 1
        total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
        has_next = (start + limit) < total_count
        has_previous = start > 0
        
        return {
            "success": True,
            "tradelines": tradelines,
            "pagination": {
                "current_page": current_page,
                "total_pages": total_pages,
                "limit": limit,
                "start": start,
                "has_next": has_next,
                "has_previous": has_previous,
                "total_records": total_count
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }
        
        
@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_tradelines_admin(limit=20, start=0, search=None, filters=None):
    """
    Get list of tradelines
    """
    try:
        query_filters = {"status": "Active"}
        
        # Convert limit and start to integers
        limit = int(limit) if limit else 20
        start = int(start) if start else 0

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

        # Handle search across multiple fields
        if search:
            search_term = f"%{search}%"
            # Use SQL query for multi-field search
            search_conditions = """(
                t.name LIKE %(search)s OR
                t.bank LIKE %(search)s OR
                t.card_holder LIKE %(search)s OR
                t.status LIKE %(search)s OR
                t.closing_date LIKE %(search)s OR
                CAST(t.credit_limit AS CHAR) LIKE %(search)s OR
                CAST(t.price AS CHAR) LIKE %(search)s OR
                CAST(t.commission AS CHAR) LIKE %(search)s OR
                CAST(t.age_year AS CHAR) LIKE %(search)s
            )"""
            
            # Build WHERE clause for filters
            where_conditions = ["t.status = 'Active'"]
            sql_values = {"search": search_term}
            
            if filters:
                if filters.get("min_price"):
                    where_conditions.append("t.price >= %(min_price)s")
                    sql_values["min_price"] = filters.get("min_price")
                if filters.get("max_price"):
                    where_conditions.append("t.price <= %(max_price)s")
                    sql_values["max_price"] = filters.get("max_price")
                if filters.get("min_credit_limit"):
                    where_conditions.append("t.credit_limit >= %(min_credit_limit)s")
                    sql_values["min_credit_limit"] = filters.get("min_credit_limit")
                if filters.get("bank"):
                    where_conditions.append("t.bank = %(bank)s")
                    sql_values["bank"] = filters.get("bank")
            
            where_conditions.append(search_conditions)
            where_clause = " AND ".join(where_conditions)
            
            # Get total count
            count_query = f"""SELECT COUNT(*) as count FROM `tabTradeline` t WHERE {where_clause}"""
            total_count = frappe.db.sql(count_query, sql_values, as_dict=True)[0].count
            
            # Get tradelines
            sql_values["limit"] = limit
            sql_values["start"] = start
            tradelines_query = f"""SELECT 
                t.name, t.bank, t.age_year, t.age_month, t.credit_limit,
                t.price, t.max_spots, t.remaining_spots, t.closing_date, t.commission, t.card_holder,
                t.credit_utilization_rate, t.status
                FROM `tabTradeline` t
                WHERE {where_clause}
                ORDER BY t.creation DESC
                LIMIT %(limit)s OFFSET %(start)s"""
            tradelines = frappe.db.sql(tradelines_query, sql_values, as_dict=True)
        else:
            # Get total count for pagination
            total_count = frappe.db.count("Tradeline", filters=query_filters)

            tradelines = frappe.get_all("Tradeline",
                filters=query_filters,
                fields=["name", "bank", "age_year", "age_month", "credit_limit", 
                       "price", "max_spots", "remaining_spots", "closing_date", "commission","card_holder",
                       "credit_utilization_rate", "status", "late_payment"],
                limit=limit,
                start=start,
                order_by="creation desc"
            )
        
        # Get bank names
        for tradeline in tradelines:
            if tradeline.bank:
                bank_doc = frappe.get_doc("Tradeline Bank", tradeline.bank)
                tradeline.bank_name = bank_doc.bank_name
            tradeline.card_holder_name = tradeline.card_holder
        
        # Calculate pagination
        current_page = (start // limit) + 1 if limit > 0 else 1
        total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
        has_next = (start + limit) < total_count
        has_previous = start > 0
        
        return {
            "success": True,
            "tradelines": tradelines,
            "pagination": {
                "current_page": current_page,
                "total_pages": total_pages,
                "limit": limit,
                "start": start,
                "has_next": has_next,
                "has_previous": has_previous,
                "total_records": total_count
            }
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

        user = get_authenticated_user()
        role_profile_name = frappe.get_value("User", user, "role_profile_name")
        if not is_administrator(user) or role_profile_name == "Tradeline Seller":
            frappe.throw(_("You do not have permission to access this resource"), frappe.PermissionError)
            
        tradeline = frappe.get_doc("Tradeline", tradeline_id)
        
        # Get related data
        bank_doc = frappe.get_doc("Tradeline Bank", tradeline.bank) if tradeline.bank else None
        card_holder_doc = frappe.get_doc("Customer", tradeline.card_holder) if tradeline.card_holder else None
        if tradeline.mailing_address:
            mailing_address_doc = frappe.get_doc("Address", tradeline.mailing_address)
        else:
            mailing_address_doc = None

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
            "commission": tradeline.commission,
            "credit_usage": tradeline.credit_usage,
            "late_payment": tradeline.late_payment,
            "card_holder": {
                "name": card_holder_doc.name if card_holder_doc else None,
                "fullname": card_holder_doc.customer_name if card_holder_doc else None,
                "email": card_holder_doc.email_id if card_holder_doc else None,
                "phone": card_holder_doc.mobile_no if card_holder_doc else None
            } if card_holder_doc else None,
            "mailing_address": mailing_address_doc.name if mailing_address_doc else None,
            "mailing_address_details": mailing_address_doc if mailing_address_doc else None
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
            "credit_usage": tradeline.credit_usage,
            "status": tradeline.status,
            "balance": tradeline.balance,
            # "mailing_address": mailing_address_doc.address if mailing_address_doc else None
    
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
@jwt_required()
def create_tradeline(bank, age_year, credit_limit, price, max_spots, 
                    closing_date, card_holder, mailing_address, 
                    age_month=None, credit_utilization_rate=None, commission=0.0, credit_usage=None,
                    balance=None, status="Active", late_payment=None):
    """
    Create new tradeline
    """
    try:
        user = get_authenticated_user()
        role_profile = frappe.db.get_value("User", user, "role_profile_name")
        if role_profile != "Administrator" and role_profile != "Tradeline Seller":
            return {
                "success": False,
                "message": f"Permission denied {role_profile}"
            }
            
        if not card_holder:
            card_holder = frappe.db.get_value("Customer", {"email_id": user}, "name")

        # Validate age_month
        if age_month is not None:
            age_month_int = int(age_month)
            if age_month_int < 1 or age_month_int > 12:
                return {
                    "success": False,
                    "message": "Age month must be between 1 and 12"
                }

        status = status if is_administrator(user) else "InActive"
        has_signed_agreement = frappe.db.get_value("Customer", dict(email_id=user), "has_signed_agreement")
        if not has_signed_agreement:
            frappe.throw(_("You must sign the authorized user agreement before creating a tradeline."), frappe.PermissionError)

        tradeline = frappe.get_doc({
            "doctype": "Tradeline",
            "bank": bank,
            "age_year": age_year,
            "age_month": age_month or 0,
            "credit_limit": credit_limit,
            "credit_usage": credit_usage or 0,
            "price": price,
            "max_spots": max_spots,
            "remaining_spots": max_spots,
            "purchased_spots": 0,
            "closing_date": closing_date,
            "commission": commission or 0.0,
            "card_holder": card_holder,
            "mailing_address": mailing_address,
            "credit_utilization_rate": credit_utilization_rate or 0,
            "balance": balance or 0,
            "status": status,
            "late_payment": late_payment
        })
        tradeline.insert(ignore_permissions=True)
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
                         "mailing_address", "credit_utilization_rate", "commission","credit_usage",
                         "balance", "status", "late_payment"]
        
        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                if field == "max_spots" and int(value) < tradeline.purchased_spots:
                    active_slots = frappe.db.count("Client Tradelines", filters={"tradeline": tradeline.name, "status": "Active"})
                    setattr(tradeline,'remaining_spots', value - active_slots)
                    frappe.throw(_("Max spots cannot be less than purchased spots"), frappe.ValidationError)
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

@frappe.whitelist(allow_guest=True)
@jwt_required()
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

@frappe.whitelist(allow_guest=True)
@jwt_required()
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
def get_banks(limit=None, start=None):
    """
    Get list of banks with optional pagination
    """
    try:
        # Get total count
        total_count = frappe.db.count("Tradeline Bank")
        
        # Build query parameters
        query_params = {
            "fields": ["name", "bank_name", "image", "status"],
            "order_by": "bank_name asc"
        }
        
        # Add pagination if limit and start are provided
        if limit is not None and start is not None:
            query_params["limit"] = int(limit)
            query_params["start"] = int(start)
        
        banks = frappe.get_all("Tradeline Bank", **query_params)
        
        # Set default status if not available
        for bank in banks:
            if not hasattr(bank, 'status') or not bank.status:
                bank.status = 'active'
        
        result = {
            "success": True,
            "banks": banks
        }
        
        # Add pagination if limit and start were provided
        if limit is not None and start is not None:
            limit = int(limit)
            start = int(start)
            current_page = (start // limit) + 1 if limit > 0 else 1
            total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
            has_next = (start + limit) < total_count
            has_previous = start > 0
            
            result["pagination"] = {
                "current_page": current_page,
                "total_pages": total_pages,
                "limit": limit,
                "start": start,
                "has_next": has_next,
                "has_previous": has_previous,
                "total_records": total_count
            }
                
        return result
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist(allow_guest=True)
@jwt_required()
def create_bank(bank_name, image=None):
    """
    Create new bank with optional image upload
    """
    try:
        user = frappe.session.user
        if not user or not frappe.has_permission("Tradeline Bank", "create"):
            return {
                "success": False,
                "message": "Permission denied"
            }
        
        # Handle image upload first
        image_url = None
        if frappe.request and hasattr(frappe.request, 'files') and frappe.request.files:
            if 'image' in frappe.request.files:
                uploaded_file = frappe.request.files['image']
                if uploaded_file and uploaded_file.filename:
                    try:
                        from frappe.utils.file_manager import save_file
                        from werkzeug.utils import secure_filename
                        import os
                        
                        # Generate secure filename
                        filename = secure_filename(uploaded_file.filename)
                        
                        # Save file as public
                        file_doc = save_file(
                            fname=filename,
                            content=uploaded_file.read(),
                            dt=None,  # Not attached to any specific document initially
                            dn=None,
                            folder='Home',
                            is_private=0  # Make it public
                        )
                        image_url = file_doc.file_url
                        
                    except Exception as e:
                        frappe.log_error(f"Image upload error during bank creation: {str(e)}")
                        return {
                            "success": False,
                            "message": f"Failed to upload image: {str(e)}"
                        }
        elif image and isinstance(image, str):
            # Handle image as URL string
            image_url = image
        
        # Create bank document
        bank_data = {
            "doctype": "Tradeline Bank",
            "bank_name": bank_name
        }
        
        if image_url:
            bank_data["image"] = image_url
        
        bank = frappe.get_doc(bank_data)
        bank.insert()
        
        # Update file attachment after bank is created
        if image_url and frappe.request and hasattr(frappe.request, 'files'):
            try:
                # Find the file document and attach it to the bank
                file_docs = frappe.get_all("File", 
                    filters={"file_url": image_url},
                    fields=["name"],
                    limit=1
                )
                if file_docs:
                    file_doc = frappe.get_doc("File", file_docs[0].name)
                    file_doc.attached_to_doctype = "Tradeline Bank"
                    file_doc.attached_to_name = bank.name
                    file_doc.attached_to_field = "image"
                    file_doc.save(ignore_permissions=True)
            except Exception as e:
                frappe.log_error(f"Error attaching file to bank: {str(e)}")
        
        frappe.db.commit()
        
        return {
            "success": True,
            "message": "Bank created successfully",
            "bank": {
                "name": bank.name,
                "bank_name": bank.bank_name,
                "image": bank.image if hasattr(bank, 'image') else None
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Bank creation failed: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist(allow_guest=True)
@jwt_required()
def update_bank(bank_name=None, status=None, image=None):
    """
    Update existing bank details with optional image upload
    """
    bank_id = bank_name
    try:
        user = frappe.session.user
        if not user or not frappe.has_permission("Tradeline Bank", "write"):
            return {
                "success": False,
                "message": "Permission denied"
            }
        
        # Check if bank exists
        if not frappe.db.exists("Tradeline Bank", bank_id):
            return {
                "success": False,
                "message": "Bank not found"
            }
        
        # Get the bank document
        bank = frappe.get_doc("Tradeline Bank", bank_id)
        
        # Handle file upload for image
        file_url = None
        if frappe.request and hasattr(frappe.request, 'files') and frappe.request.files:
            if 'image' in frappe.request.files:
                uploaded_file = frappe.request.files['image']
                if uploaded_file and uploaded_file.filename:
                    try:
                        from frappe.utils.file_manager import save_file
                        from werkzeug.utils import secure_filename
                        import os
                        
                        # Generate secure filename
                        filename = secure_filename(uploaded_file.filename)
                        
                        # Save file as public
                        file_doc = save_file(
                            fname=filename,
                            content=uploaded_file.read(),
                            dt="Tradeline Bank",
                            dn=bank_id,
                            folder='Home',
                            is_private=0  # Make it public
                        )
                        file_url = file_doc.file_url
                        
                    except Exception as e:
                        frappe.log_error(f"Image upload error during bank update: {str(e)}")
                        return {
                            "success": False,
                            "message": f"Failed to upload image: {str(e)}"
                        }
        
        # Update bank fields
        updated_fields = []
        
        if bank_name is not None:
            bank.bank_name = bank_name
            updated_fields.append("bank_name")
        
        if status is not None:
            # Validate status value
            valid_statuses = ["active", "inactive"]
            if status.lower() not in valid_statuses:
                return {
                    "success": False,
                    "message": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
                }
            bank.status = status.lower()
            updated_fields.append("status")
        
        if file_url:
            bank.image = file_url
            updated_fields.append("image")
        elif image is not None and image != "":
            # If image is provided as URL string
            bank.image = image
            updated_fields.append("image")
        
        # Save the bank document
        bank.save(ignore_permissions=True)
        frappe.db.commit()
        
        return {
            "success": True,
            "message": f"Bank updated successfully. Updated fields: {', '.join(updated_fields)}",
            "bank": {
                "name": bank.name,
                "bank_name": bank.bank_name,
                "status": getattr(bank, 'status', 'active'),
                "image": bank.image,
                "updated_fields": updated_fields
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Bank update failed: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }
    
@frappe.whitelist(allow_guest=True)
@jwt_required()
def delete_bank(bank_name):
    """
    Delete a bank
    """
    try:
        user = frappe.session.user
        if not user or not frappe.has_permission("Tradeline Bank", "delete"):
            return {
                "success": False,
                "message": "Permission denied"
            }
        
        # Check if bank exists
        if not frappe.db.exists("Tradeline Bank", bank_name):
            return {
                "success": False,
                "message": "Bank not found"
            }
        
        # Check if bank is being used by any tradelines
        tradelines_using_bank = frappe.db.count("Tradeline", filters={"bank": bank_name})
        if tradelines_using_bank > 0:
            return {
                "success": False,
                "message": f"Cannot delete bank. It is currently being used by {tradelines_using_bank} tradeline(s). Please remove or reassign these tradelines first."
            }
        
        # Get bank details before deletion for response
        bank = frappe.get_doc("Tradeline Bank", bank_name)
        bank_name = bank.bank_name
        
        # Delete associated files if any
        try:
            files = frappe.get_all("File", 
                filters={
                    "attached_to_doctype": "Tradeline Bank",
                    "attached_to_name": bank_name
                },
                fields=["name"]
            )
            for file_doc in files:
                frappe.delete_doc("File", file_doc.name, ignore_permissions=True)
        except Exception as file_error:
            frappe.log_error(f"Error deleting associated files: {str(file_error)}")
        
        # Delete the bank
        frappe.delete_doc("Tradeline Bank", bank_name, ignore_permissions=True)
        frappe.db.commit()
        
        return {
            "success": True,
            "message": f"Bank '{bank_name}' deleted successfully",
            "deleted_bank": {
                "name": bank_name,
                "bank_name": bank_name
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Bank deletion failed: {str(e)}")
        return {
            "success": False,
            "message": str(e)
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
                   "total_amount", "creation", "modified", "owner", "modified_by",
                   "refund_username", "refund_security_question", "refund_security_answer", "refund_pin", "refund_reason", "refund_link"],
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
                    "status": client_tradeline.status,
                    "refund_username": client_tradeline.refund_username,
                    "refund_security_question": client_tradeline.refund_security_question,
                    "refund_security_answer": client_tradeline.refund_security_answer,
                    "refund_pin": client_tradeline.refund_pin,
                    "refund_reason": client_tradeline.refund_reason,
                    "refund_link": client_tradeline.refund_link
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
                        "new_status": client_tradeline.status,
                        "refund_username": client_tradeline.refund_username if client_tradeline.status == "Refund Requested" else None,
                        "refund_security_question": client_tradeline.refund_security_question if client_tradeline.status == "Refund Requested" else None,
                        "refund_security_answer": client_tradeline.refund_security_answer if client_tradeline.status == "Refund Requested" else None,
                        "refund_pin": client_tradeline.refund_pin if client_tradeline.status == "Refund Requested" else None,
                        "refund_reason": client_tradeline.refund_reason if client_tradeline.status == "Refund Requested" else None,
                        "refund_link": client_tradeline.refund_link if client_tradeline.status == "Refund Requested" else None
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
            "timeline_items": timeline_items
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


@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_seller_tradelines(limit=20, start=0, search=None, filters=None):
    """
    Get list of tradelines
    """
    try:
        user = get_authenticated_user()
        customer = frappe.db.get_value("Customer", {"email_id": user}, "name")
        query_filters = dict(card_holder=customer)

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

        # Convert limit and start to integers
        limit = int(limit) if limit else 20
        start = int(start) if start else 0

        # Get total count for pagination
        total_count = frappe.db.count("Tradeline", filters=query_filters)

        tradelines = frappe.get_all("Tradeline",
            filters=query_filters,
            fields=["name", "bank", "age_year", "age_month", "credit_limit", 
                   "price", "max_spots", "remaining_spots", "closing_date", 
                   "credit_utilization_rate", "status", "late_payment"],
            limit=limit,
            start=start,
            order_by="creation desc"
        )
        
        # Get bank names
        for tradeline in tradelines:
            if tradeline.bank:
                bank_doc = frappe.get_doc("Tradeline Bank", tradeline.bank)
                tradeline.bank_name = bank_doc.bank_name

        # Calculate pagination
        current_page = (start // limit) + 1 if limit > 0 else 1
        total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
        has_next = (start + limit) < total_count
        has_previous = start > 0
        
        return {
            "success": True,
            "data": tradelines,
            "message": "Tradelines retrieved successfully",
            "pagination": {
                "current_page": current_page,
                "total_pages": total_pages,
                "limit": limit,
                "start": start,
                "has_next": has_next,
                "has_previous": has_previous,
                "total_records": total_count
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve tradelines"
        }
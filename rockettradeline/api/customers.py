import frappe
from frappe import _
from frappe.utils import flt, now_datetime, getdate
from .auth import jwt_required, get_authenticated_user
from .utils import is_administrator


@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_customers(customer_type=None, is_seller=None, is_buyer=None, status=None, limit=50, start=0, search=None, role_profile_name=None):
    """Get customers list (Admin only)"""
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.throw(_("Authentication required"))

        # Check if user is administrator
        is_admin = is_administrator(current_user)
        
        if not is_admin:
            frappe.throw(_("Access denied. Only administrators can access customer data."))
        
        # Build base query conditions
        conditions = []
        
        # Filter by customer type if provided
        if customer_type:
            conditions.append(f"customer_type = '{customer_type}'")
        
        # Filter by seller status if provided
        if is_seller is not None:
            seller_filter = "1" if str(is_seller).lower() in ['true', '1', 'yes'] else "0"
            conditions.append(f"is_seller = {seller_filter}")
        
        # Filter by buyer status if provided (assuming non-sellers are buyers)
        if is_buyer is not None:
            buyer_filter = "1" if str(is_buyer).lower() in ['true', '1', 'yes'] else "0"
            if buyer_filter == "1":
                conditions.append("(is_seller = 0 OR is_seller IS NULL)")
            else:
                conditions.append("is_seller = 1")
        
        # Filter by status if provided
        if status:
            if status.lower() == "active":
                conditions.append("c.disabled = 0")
            elif status.lower() == "disabled":
                conditions.append("c.disabled = 1")
        
        # Filter by role profile name if provided
        if role_profile_name:
            conditions.append(f"u.role_profile_name = '{role_profile_name}'")
        
        # Add search functionality
        if search:
            search_value = search.replace("'", "''")  # Escape single quotes
            search_conditions = [
                f"c.customer_name LIKE '%{search_value}%'",
                f"c.email_id LIKE '%{search_value}%'", 
                f"c.mobile_no LIKE '%{search_value}%'",
                f"c.customer_group LIKE '%{search_value}%'",
                f"u.role_profile_name LIKE '%{search_value}%'"
            ]
            conditions.append(f"({' OR '.join(search_conditions)})")
        
        # Build WHERE clause
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
        
        # Get total count (using JOIN for role_profile_name filter)
        count_query = f"""
            SELECT COUNT(*) as total
            FROM `tabCustomer` c
            LEFT JOIN `tabUser` u ON u.name = c.email_id
            {where_clause}
        """
        
        total_result = frappe.db.sql(count_query, as_dict=True)
        total = total_result[0].total if total_result else 0
        
        # Get paginated results
        query = f"""
            SELECT 
                c.name,
                c.customer_name,
                c.customer_type,
                c.customer_group,
                c.territory,
                c.email_id,
                c.mobile_no,
                c.website,
                c.is_seller,
                c.disabled,
                c.creation,
                c.modified,
                c.tax_id,
                c.customer_primary_contact,
                c.customer_primary_address,
                c.default_currency,
                c.default_price_list,
                c.payment_terms,
                u.role_profile_name
            FROM `tabCustomer` c
            LEFT JOIN `tabUser` u ON u.name = c.email_id
            {where_clause}
            ORDER BY c.modified DESC
            LIMIT {int(limit)} OFFSET {int(start)}
        """
        
        customers = frappe.db.sql(query, as_dict=True)
        
        # Get additional customer statistics
        stats_query = f"""
            SELECT 
                COUNT(*) as total_customers,
                SUM(CASE WHEN c.is_seller = 1 THEN 1 ELSE 0 END) as total_sellers,
                SUM(CASE WHEN (c.is_seller = 0 OR c.is_seller IS NULL) THEN 1 ELSE 0 END) as total_buyers,
                SUM(CASE WHEN c.disabled = 0 THEN 1 ELSE 0 END) as active_customers,
                SUM(CASE WHEN c.disabled = 1 THEN 1 ELSE 0 END) as disabled_customers
            FROM `tabCustomer` c
            LEFT JOIN `tabUser` u ON u.name = c.email_id
            {where_clause}
        """
        
        stats_result = frappe.db.sql(stats_query, as_dict=True)
        stats = stats_result[0] if stats_result else {}
        
        # Format the response
        formatted_customers = []
        for customer in customers:
            # Get customer's cart and payment history counts
            cart_count = frappe.db.count("Tradeline Cart", {"customer": customer.name})
            payment_count = frappe.db.count("Payment Request", {"customer_email": customer.email_id})
            client_tradelines_count = frappe.db.count("Client Tradelines", {"customer": customer.name})
            
            # Get primary address information if available
            address_info = {
                "address_line1": None,
                "address_line2": None,
                "city": None,
                "state": None,
                "pincode": None,
                "country": None
            }
            
            if customer.customer_primary_address:
                try:
                    address_doc = frappe.get_doc("Address", customer.customer_primary_address)
                    address_info = {
                        "address_line1": address_doc.address_line1,
                        "address_line2": getattr(address_doc, 'address_line2', None),
                        "city": address_doc.city,
                        "state": address_doc.state,
                        "pincode": address_doc.pincode,
                        "country": address_doc.country
                    }
                except:
                    pass  # Keep default None values if address can't be fetched
            
            formatted_customer = {
                "id": customer.name,
                "customer_name": customer.customer_name,
                "customer_type": customer.customer_type,
                "customer_group": customer.customer_group,
                "territory": customer.territory,
                "email_id": customer.email_id,
                "mobile_no": customer.mobile_no,
                "website": customer.website,
                "is_seller": bool(customer.is_seller) if customer.is_seller else False,
                "is_buyer": not bool(customer.is_seller) if customer.is_seller else True,
                "status": "Active" if not customer.disabled else "Disabled",
                "disabled": bool(customer.disabled) if customer.disabled else False,
                "creation": customer.creation,
                "modified": customer.modified,
                "role_profile_name": customer.role_profile_name,
                "address": address_info,
                "financial": {
                    "tax_id": customer.tax_id,
                    "default_currency": customer.default_currency,
                    "default_price_list": customer.default_price_list,
                    "payment_terms": customer.payment_terms
                },
                "contacts": {
                    "primary_contact": customer.customer_primary_contact,
                    "primary_address": customer.customer_primary_address
                },
                "activity_summary": {
                    "total_carts": cart_count,
                    "total_payments": payment_count,
                    "total_client_tradelines": client_tradelines_count
                },
               
            }
            formatted_customers.append(formatted_customer)
        
        # Calculate pagination
        current_page = (int(start) // int(limit)) + 1 if int(limit) > 0 else 1
        total_pages = (total + int(limit) - 1) // int(limit) if int(limit) > 0 else 1
        has_next = (int(start) + int(limit)) < total
        has_previous = int(start) > 0
        
        return {
            "success": True,
            "data": formatted_customers,
            "pagination": {
                "current_page": current_page,
                "total_pages": total_pages,
                "limit": int(limit),
                "start": int(start),
                "has_next": has_next,
                "has_previous": has_previous,
                "total_records": total
            },
            "statistics": {
                "total_customers": stats.get("total_customers", 0),
                "total_sellers": stats.get("total_sellers", 0),
                "total_buyers": stats.get("total_buyers", 0),
                "active_customers": stats.get("active_customers", 0),
                "disabled_customers": stats.get("disabled_customers", 0)
            },
            "filters_applied": {
                "customer_type": customer_type,
                "is_seller": is_seller,
                "is_buyer": is_buyer,
                "status": status,
                "search": search,
                "role_profile_name": role_profile_name
            },
            "user": current_user,
            "is_admin": is_admin
        }

    except Exception as e:
        frappe.throw(f"Failed to fetch customers: {str(e)}")


@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_customer_details(customer_id):
    """Get detailed information about a specific customer (Admin only)"""
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.throw(_("Authentication required"))

        # Check if user is administrator
        is_admin = is_administrator(current_user)
        
         # Get the customer document
        customer_doc = frappe.get_doc("Customer", customer_id)
        user = frappe.get_doc("User", customer_doc.email_id)
    
       
        account_manager = customer_doc.account_manager
        if account_manager and account_manager != current_user and not is_admin:
            frappe.throw(_("Access denied. You are not the account manager for this customer."))
        
        # Get related documents and statistics
        cart_docs = frappe.get_all("Tradeline Cart", 
            filters={"customer": customer_id}, 
            fields=["name", "status", "total_amount", "creation", "modified"],
            order_by="modified desc",
            limit=10)
        
        payment_docs = frappe.get_all("Payment Request", 
            filters={"customer_email": customer_doc.email_id}, 
            fields=["name", "status", "total_amount", "payment_method", "creation", "modified"],
            order_by="modified desc",
            limit=10)
        
        client_tradelines_docs = frappe.get_all("Client Tradelines", 
            filters={"customer": customer_id}, 
            fields=["name", "title", "status", "total_amount", "tradeline_name", "creation", "modified"],
            order_by="modified desc",
            limit=10)
        
        # Get customer addresses
        addresses = frappe.get_all("Address", 
            filters={"link_doctype": "Customer", "link_name": customer_id}, 
            fields=["name", "address_title", "address_type", "address_line1", "address_line2", "city", "state", "pincode", "country", "is_primary_address"])
        
        # Get customer contacts
        contacts = frappe.get_all("Contact", 
            filters={"link_doctype": "Customer", "link_name": customer_id}, 
            fields=["name", "first_name", "last_name", "email_id", "phone", "mobile_no", "is_primary_contact"])
        
        # Get customer files/attachments
        files = []
        try:
            file_docs = frappe.get_all("File", 
                filters={
                    "attached_to_doctype": "Customer",
                    "attached_to_name": customer_id
                }, 
                fields=["name", "file_name", "file_url", "file_size", "creation", "modified", "owner"]
            )
            
            for file_doc in file_docs:
                files.append({
                    "name": file_doc.name,
                    "file_name": file_doc.file_name,
                    "file_url": file_doc.file_url,
                    "file_size": file_doc.file_size,
                    "creation": file_doc.creation,
                    "modified": file_doc.modified,
                    "uploaded_by": file_doc.owner
                })
        except Exception as e:
            frappe.log_error(f"Error fetching customer files: {str(e)}", "Customer Files Error")
        
        # Calculate totals
        total_cart_amount = sum(float(cart.total_amount or 0) for cart in cart_docs)
        total_payment_amount = sum(float(payment.total_amount or 0) for payment in payment_docs)
        total_tradeline_amount = sum(float(tradeline.total_amount or 0) for tradeline in client_tradelines_docs)
        
        # Format the response
        response = {
            "success": True,
            "customer": {
                "id": customer_doc.name,
                "customer_name": customer_doc.customer_name,
                "customer_type": customer_doc.customer_type,
                "customer_group": customer_doc.customer_group,
                "territory": customer_doc.territory,
                "email_id": customer_doc.email_id,
                "mobile_no": customer_doc.mobile_no,
                "website": customer_doc.website,
                "is_seller": bool(customer_doc.is_seller) if hasattr(customer_doc, 'is_seller') and customer_doc.is_seller else False,
                "is_buyer": not bool(customer_doc.is_seller) if hasattr(customer_doc, 'is_seller') and customer_doc.is_seller else True,
                "status": "Active" if not customer_doc.disabled else "Disabled",
                "disabled": bool(customer_doc.disabled),
                "creation": customer_doc.creation,
                "modified": customer_doc.modified,
                "tax_id": customer_doc.tax_id,
                "default_currency": customer_doc.default_currency,
                "default_price_list": customer_doc.default_price_list,
                "payment_terms": customer_doc.payment_terms
            },
            "addresses": addresses,
            "contacts": contacts,
            "files": files,
            "recent_activity": {
                "carts": cart_docs,
                "payments": payment_docs,
                "client_tradelines": client_tradelines_docs
            },
            "financial_summary": {
                "total_cart_amount": total_cart_amount,
                "total_payment_amount": total_payment_amount,
                "total_tradeline_amount": total_tradeline_amount,
                "total_carts": len(cart_docs),
                "total_payments": len(payment_docs),
                "total_client_tradelines": len(client_tradelines_docs),
                "total_files": len(files)
            },
            "user": dict(dob=user.birth_date, role_profile_name=user.role_profile_name),
            "is_admin": is_admin
        }
        
        return response

    except Exception as e:
        frappe.throw(f"Failed to fetch customer details: {str(e)}")


@frappe.whitelist(allow_guest=True)
@jwt_required()
def update_customer_status(customer_id, disabled=None, is_seller=None):
    """Update customer status and flags (Admin only)"""
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.throw(_("Authentication required"))

        # Check if user is administrator
        is_admin = is_administrator(current_user)
        
        if not is_admin:
            frappe.throw(_("Access denied. Only administrators can update customer status."))
        
        # Get the customer document
        customer_doc = frappe.get_doc("Customer", customer_id)
        
        updates_made = []
        
        # Update disabled status
        if disabled is not None:
            old_disabled = customer_doc.disabled
            new_disabled = 1 if str(disabled).lower() in ['true', '1', 'yes'] else 0
            if old_disabled != new_disabled:
                customer_doc.disabled = new_disabled
                user_doc = frappe.get_doc("User", customer_doc.email_id)
                user_doc.enabled = 0 if new_disabled else 1
                user_doc.save(ignore_permissions=True)
                frappe.db.commit()
                
                updates_made.append(f"Status changed from {'Disabled' if old_disabled else 'Active'} to {'Disabled' if new_disabled else 'Active'}")
        
        # Update seller status
        if is_seller is not None:
            old_seller = getattr(customer_doc, 'is_seller', 0)
            new_seller = 1 if str(is_seller).lower() in ['true', '1', 'yes'] else 0
            if old_seller != new_seller:
                customer_doc.is_seller = new_seller
                updates_made.append(f"Seller status changed from {bool(old_seller)} to {bool(new_seller)}")
        
        if updates_made:
            customer_doc.save(ignore_permissions=True)
            frappe.db.commit()
        
        return {
            "success": True,
            "message": f"Customer updated successfully" + (f": {', '.join(updates_made)}" if updates_made else " (no changes made)"),
            "customer_id": customer_id,
            "updates_made": updates_made,
            "updated_by": current_user,
            "updated_at": now_datetime(),
            "current_status": {
                "disabled": bool(customer_doc.disabled),
                "is_seller": bool(getattr(customer_doc, 'is_seller', 0))
            }
        }

    except Exception as e:
        frappe.throw(f"Failed to update customer status: {str(e)}")


@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_customer_types():
    """Get all available customer types (Admin only)"""
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.throw(_("Authentication required"))

        # Check if user is administrator
        is_admin = is_administrator(current_user)
        
        if not is_admin:
            frappe.throw(_("Access denied. Only administrators can access customer type data."))
        
        # Get customer types from Customer Type doctype
        customer_types = frappe.get_all("Customer Type", 
            fields=["name", "creation", "modified"],
            order_by="name")
        
        # Get customer groups
        customer_groups = frappe.get_all("Customer Group", 
            fields=["name", "parent_customer_group", "is_group", "creation", "modified"],
            order_by="name")
        
        # Get territories
        territories = frappe.get_all("Territory", 
            fields=["name", "parent_territory", "is_group", "creation", "modified"],
            order_by="name")
        
        return {
            "success": True,
            "customer_types": customer_types,
            "customer_groups": customer_groups,
            "territories": territories,
            "user": current_user,
            "is_admin": is_admin
        }

    except Exception as e:
        frappe.throw(f"Failed to fetch customer types: {str(e)}")

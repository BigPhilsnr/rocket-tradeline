import frappe
from frappe import _
from frappe.utils import flt, now_datetime
from decimal import Decimal
import json
import re
from .auth import jwt_required, get_authenticated_user, get_email_header, get_email_footer


def send_payment_request_notification_email(payment_request_doc):
    """Send email notification to admin when payment request is created"""
    try:
        # Get consistent email header and footer
        email_header = get_email_header()
        email_footer = get_email_footer("info@rockettradeline.com")
        
        # Format payment request details for email
        payment_details = f"""{email_header}
        <h3 style="color: #374151; margin: 0 0 20px 0;">New Payment Request Created</h3>
        <div style="background-color: #f9fafb; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
            <p style="margin: 5px 0;"><strong>Payment Request ID:</strong> {payment_request_doc.name}</p>
            <p style="margin: 5px 0;"><strong>Customer:</strong> {payment_request_doc.customer_name} ({payment_request_doc.customer_email})</p>
            <p style="margin: 5px 0;"><strong>Payment Method:</strong> {payment_request_doc.payment_method}</p>
            <p style="margin: 5px 0;"><strong>Amount:</strong> ${payment_request_doc.amount:.2f}</p>
            <p style="margin: 5px 0;"><strong>Total Amount:</strong> ${payment_request_doc.total_amount:.2f}</p>
            <p style="margin: 5px 0;"><strong>Cart ID:</strong> {payment_request_doc.cart_id}</p>
            <p style="margin: 5px 0;"><strong>Status:</strong> {payment_request_doc.status}</p>
            <p style="margin: 5px 0;"><strong>Created At:</strong> {payment_request_doc.created_at}</p>
        </div>
        
        <h4 style="color: #374151; margin: 20px 0 15px 0;">Action Required:</h4>
        <p style="color: #6b7280; line-height: 1.6; margin: 0 0 20px 0;">
            Please log in to the admin portal to review and approve this payment request.
        </p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="https://rocket-app.tiberbuhealth.com/app/payment-request/{payment_request_doc.name}" 
               style="background-color: #17B26A; color: white; padding: 12px 24px; text-decoration: none; 
                      border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">
                View Payment Request
            </a>
        </div>
        {email_footer}"""
        
        # Send email to admin
        frappe.sendmail(
            recipients=["info@rockettradeline.com"],
            subject=f"New Payment Request - {payment_request_doc.name}",
            message=payment_details,
            header=["New Payment Request Notification"],
            delayed=False
        )
        
        frappe.logger().info(f"Payment request notification email sent for {payment_request_doc.name}")
        return True
        
    except Exception as e:
        frappe.log_error(f"Failed to send payment request notification email: {str(e)}", "Email Notification Error")
        return False


def send_payment_approval_email(payment_request_doc):
    """Send email notification to customer when payment is approved"""
    try:
        # Get cart details
        cart = frappe.get_doc("Tradeline Cart", payment_request_doc.cart_id)
        cart_items = cart.get("items", [])
        
        # Format tradeline details
        tradeline_details = ""
        if cart_items:
            tradeline_details = "<h4 style='color: #374151; margin: 20px 0 15px 0;'>Your Tradelines:</h4><ul style='margin: 0 0 20px 20px; padding: 0;'>"
            for item in cart_items:
                tradeline_details += f"<li style='margin: 5px 0; color: #6b7280;'>{item.tradeline_name} - ${item.amount:.2f}</li>"
            tradeline_details += "</ul>"
        
        # Get consistent email header and footer
        email_header = get_email_header()
        email_footer = get_email_footer(payment_request_doc.customer_email)
        
        # Format approval email
        approval_message = f"""{email_header}
        <h3 style="color: #17B26A; margin: 0 0 20px 0;">Payment Approved - Tradelines Activated!</h3>
        <p style="color: #374151; font-size: 16px; margin: 0 0 10px 0;">Dear {payment_request_doc.customer_name},</p>
        
        <p style="color: #6b7280; line-height: 1.6; font-size: 16px; margin: 0 0 25px 0;">
            Great news! Your payment request has been approved and your tradelines are now active in your portal.
        </p>
        
        <h4 style="color: #374151; margin: 20px 0 15px 0;">Payment Details:</h4>
        <div style="background-color: #f9fafb; padding: 20px; border-radius: 6px; margin-bottom: 25px;">
            <p style="margin: 5px 0;"><strong>Payment Request ID:</strong> {payment_request_doc.name}</p>
            <p style="margin: 5px 0;"><strong>Payment Method:</strong> {payment_request_doc.payment_method}</p>
            <p style="margin: 5px 0;"><strong>Total Amount Paid:</strong> ${payment_request_doc.total_amount:.2f}</p>
            <p style="margin: 5px 0;"><strong>Transaction ID:</strong> {payment_request_doc.transaction_id or 'N/A'}</p>
            <p style="margin: 5px 0;"><strong>Approved At:</strong> {payment_request_doc.approved_at}</p>
        </div>
        
        {tradeline_details}
        
        <h4 style="color: #374151; margin: 20px 0 15px 0;">Next Steps:</h4>
        <ol style="margin: 0 0 25px 20px; padding: 0; color: #6b7280; line-height: 1.6;">
            <li style="margin: 5px 0;">Log in to your portal to view your active tradelines</li>
            <li style="margin: 5px 0;">Monitor your credit report for the new tradelines (typically appears within 30-60 days)</li>
            <li style="margin: 5px 0;">Contact our support team if you have any questions</li>
        </ol>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="https://rocket-app.tiberbuhealth.com/app" 
               style="background-color: #17B26A; color: white; padding: 12px 24px; text-decoration: none; 
                      border-radius: 6px; font-weight: 600; font-size: 16px; display: inline-block;">
                Access Your Portal
            </a>
        </div>
        
        <p style="color: #6b7280; margin: 25px 0 0 0; font-size: 16px;">
            Thank you for choosing RocketTradeline!
        </p>
        
        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 25px 0;">
        <p style="font-size: 12px; color: #9ca3af; margin: 0;">
            If you have any questions, please contact us at info@rockettradeline.com
        </p>
        {email_footer}"""
        
        # Send email to customer
        frappe.sendmail(
            recipients=[payment_request_doc.customer_email],
            subject=f"Payment Approved - Your Tradelines Are Active!",
            message=approval_message,
            header=["Payment Approved"],
            delayed=False
        )
        
        frappe.logger().info(f"Payment approval email sent to {payment_request_doc.customer_email}")
        return True
        
    except Exception as e:
        frappe.log_error(f"Failed to send payment approval email: {str(e)}", "Email Notification Error")
        return False


@frappe.whitelist(allow_guest=True)
@jwt_required()
def create_manual_payment_request(cart_id, payment_method):
    """Create a manual payment request that requires approval"""
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            return {"success": False, "error": "Authentication required"}
        
        # Handle file upload from frappe.request.files
        file_url = None
        file_upload_info = {}
        
        # Check if a file was uploaded
        if frappe.request and hasattr(frappe.request, 'files') and frappe.request.files:
            if 'proof_of_payment' in frappe.request.files:
                uploaded_file = frappe.request.files['proof_of_payment']
                if uploaded_file and uploaded_file.filename:
                    try:
                        # Save the uploaded file
                        file_doc = frappe.get_doc({
                            "doctype": "File",
                            "file_name": uploaded_file.filename,
                            "is_private": 1,
                            "content": uploaded_file.read()
                        })
                        file_doc.save(ignore_permissions=True)
                        file_url = file_doc.file_url
                        file_upload_info = {
                            "file_name": file_doc.file_name,
                            "file_size": file_doc.file_size
                        }
                    except Exception as e:
                        frappe.log_error(f"File upload error: {str(e)}")
                        return {"success": False, "error": f"Failed to upload file: {str(e)}"}
        
        # Validate cart exists and is owned by current user or user is administrator
        cart = frappe.get_doc("Tradeline Cart", cart_id)
        if cart.user_id != current_user and current_user != "Administrator" and "Administrator" not in frappe.get_roles(current_user):
            return {"success": False, "error": f"Cart not found or access denied cart belong to {cart.user_id}  not {current_user}"}

        # if cart.status != "Active":
        #     return {"success": False, "error": "Cart is not active"}

        # Calculate total amount
        cart_total = cart.calculate_totals()
        total_amount = cart_total["total"]

        # Validate payment method
        valid_methods = ["Apple Cash", "Zelle", "CashApp", "Venmo", "Bank Transfer", "Cash", "Check", "Other"]
        if payment_method not in valid_methods:
            return {"success": False, "error": f"Invalid payment method. Must be one of: {', '.join(valid_methods)}"}

        # Create manual Payment Request document
        payment_doc = frappe.get_doc({
            "doctype": "Payment Request",
            "title": f"Manual Payment - {cart_id} - {now_datetime().strftime('%Y%m%d%H%M%S')}",
            "payment_method": payment_method,
            "cart_id": cart_id,
            "amount": total_amount,
            "fees": 0,  # No fees for manual payments
            "total_amount": total_amount,
            "customer_email": current_user,
            "status": "Pending",
            "created_by": current_user,
            "created_at": now_datetime(),
            "reference_doctype": "Tradeline Cart",
            "reference_name": cart_id,
            "is_manual_payment": 1,
            "approval_status": "Pending Approval",
            "proof_of_payment": file_url,
            "instructions": f"Manual payment submission for {payment_method}. Awaiting admin approval."
        })

        payment_doc.insert(ignore_permissions=True)
        
        # If we have a file, link it to the Payment Request
        if file_url:
            try:
                # Update the File document to link it to the Payment Request
                frappe.db.sql("""
                    UPDATE `tabFile` 
                    SET attached_to_doctype = %s, attached_to_name = %s, attached_to_field = %s
                    WHERE file_url = %s
                """, ("Payment Request", payment_doc.name, "proof_of_payment", file_url))
            except Exception as attach_error:
                frappe.log_error(f"Attachment linking error: {str(attach_error)}")
        
        frappe.db.commit()

        return {
            "success": True,
            "message": "Manual payment request created successfully. Awaiting approval.",
            "payment_request_id": payment_doc.name,
            "cart_id": cart_id,
            "payment_method": payment_method,
            "amount": total_amount,
            "approval_status": "Pending Approval",
            "proof_of_payment_url": file_url,
            "has_attachment": bool(file_url),
            **file_upload_info
        }

    except Exception as e:
        frappe.log_error(f"Sample payment creation failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=True)
@jwt_required()
def upload_payment_proof(payment_request_id):
    """
    Upload proof of payment file for existing payment request
    
    Args:
        payment_request_id: Payment Request ID
        
    Returns:
        dict: Upload result
    """
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            return {"success": False, "error": "Authentication required"}
        
        # Get payment request
        payment_req = frappe.get_doc("Payment Request", payment_request_id)
        
        # Check permissions - user must be creator or admin
        if (payment_req.created_by != current_user and 
            not frappe.has_permission("Payment Request", "write") and 
            current_user != "Administrator"):
            return {"success": False, "error": "Insufficient permissions"}
        
        # Handle file upload from frappe.request.files
        file_url = None
        file_name = None
        
        if frappe.request and hasattr(frappe.request, 'files') and frappe.request.files:
            if 'proof_file' in frappe.request.files:
                uploaded_file = frappe.request.files['proof_file']
                if uploaded_file and uploaded_file.filename:
                    try:
                        # Save the uploaded file
                        file_doc = frappe.get_doc({
                            "doctype": "File",
                            "file_name": uploaded_file.filename,
                            "is_private": 1,
                            "content": uploaded_file.read()
                        })
                        file_doc.save(ignore_permissions=True)
                        file_url = file_doc.file_url
                        file_name = file_doc.file_name
                    except Exception as e:
                        frappe.log_error(f"File upload error: {str(e)}")
                        return {"success": False, "error": f"Failed to upload file: {str(e)}"}
                else:
                    return {"success": False, "error": "No file selected"}
            else:
                return {"success": False, "error": "No file field found in request"}
        else:
            return {"success": False, "error": "No files in request"}
        
        # Update payment request with file
        payment_req.proof_of_payment = file_url
        payment_req.save(ignore_permissions=True)
        
        # Link file to payment request
        frappe.db.sql("""
            UPDATE `tabFile` 
            SET attached_to_doctype = %s, attached_to_name = %s, attached_to_field = %s
            WHERE file_url = %s
        """, ("Payment Request", payment_req.name, "proof_of_payment", file_url))
        
        frappe.db.commit()
        
        return {
            "success": True,
            "message": "Proof of payment uploaded successfully",
            "payment_request_id": payment_request_id,
            "file_url": file_url,
            "file_name": file_name
        }
        
    except Exception as e:
        frappe.log_error(f"Payment proof upload failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


def is_administrator(user):
    """Check if user has Administrator role or profile"""
    if user == "Administrator":
        return True
    
    # Check if user has Administrator role profile
    user_roles = frappe.get_roles(user)
    return "System Manager" in user_roles

@frappe.whitelist(allow_guest=True)
@jwt_required()
def approve_manual_payment(payment_request_id, approval_action="approve", rejection_reason=None):
    """Approve or reject a manual payment request (Admin only)"""
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            return {"success": False, "error": "Authentication required"}
        
        # Check if user has admin permissions
        if not is_administrator(current_user):
            return {"success": False, "error": "Insufficient permissions. Admin access required."}

        # Get payment request
        payment_req = frappe.get_doc("Payment Request", payment_request_id)
        
        if not payment_req.is_manual_payment:
            return {"success": False, "error": "This is not a manual payment request"}
        
        if payment_req.approval_status != "Pending Approval":
            return {"success": False, "error": f"Payment request is already {payment_req.approval_status.lower()}"}

        if approval_action == "approve":
            # Approve the payment
            payment_req.approval_status = "Approved"
            payment_req.approved_by = current_user
            payment_req.approved_at = now_datetime()
            payment_req.status = "Draft"  # Set to Draft as requested
            
            # Create transaction ID
            payment_req.transaction_id = f"MANUAL_{payment_req.payment_method.upper()}_{now_datetime().strftime('%Y%m%d%H%M%S')}"
            
            message = "Manual payment request approved successfully"
            
        elif approval_action == "reject":
            # Reject the payment
            payment_req.approval_status = "Rejected"
            payment_req.status = "Failed"
            payment_req.rejection_reason = rejection_reason or "Payment rejected by admin"
            
            message = "Manual payment request rejected"
            
        else:
            return {"success": False, "error": "Invalid approval action. Use 'approve' or 'reject'"}

        payment_req.save(ignore_permissions=True)
        frappe.db.commit()

        return {
            "success": True,
            "message": message,
            "payment_request_id": payment_request_id,
            "approval_status": payment_req.approval_status,
            "status": payment_req.status
        }

    except Exception as e:
        frappe.log_error(f"Manual payment approval failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_manual_payment_requests(status=None, limit=20, start=0):
    """Get manual payment requests (Admin only)"""
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            return {"success": False, "error": "Authentication required"}
        
        # Check if user has admin permissions
        if not frappe.has_permission("Payment Request", "read") and current_user != "Administrator":
            return {"success": False, "error": "Insufficient permissions. Admin access required."}

        # Convert pagination parameters to integers
        limit = int(limit or 20)
        start = int(start or 0)

        filters = {"is_manual_payment": 1}
        if status:
            filters["approval_status"] = status

        manual_payments = frappe.get_all(
            "Payment Request",
            filters=filters,
            fields=[
                "name", "title", "payment_method", "cart_id", "amount", "total_amount",
                "customer", "customer_name", "customer_email", "status", "approval_status", 
                "created_by", "created_at", "approved_by", "approved_at", "rejection_reason", 
                "proof_of_payment"
            ],
            order_by="created_at desc",
            limit_start=start,
            limit_page_length=limit
        )

        # Calculate pagination info
        total_count = frappe.db.count("Payment Request", filters)
        current_page = (start // limit) + 1 if limit > 0 else 1
        total_pages = (total_count + limit - 1) // limit if limit > 0 else 1

        return {
            "success": True,
            "manual_payments": manual_payments,
            "pagination": {
                "current_page": current_page,
                "total_pages": total_pages,
                "limit": limit,
                "start": start,
                "has_next": start + limit < total_count,
                "has_previous": start > 0,
                "total_records": total_count
            }
        }

    except Exception as e:
        frappe.log_error(f"Failed to get manual payment requests: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_my_manual_payments(limit=20, start=0):
    """Get current user's manual payment requests"""
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            return {"success": False, "error": "Authentication required"}

        # Convert pagination parameters to integers
        limit = int(limit or 20)
        start = int(start or 0)

        manual_payments = frappe.get_all(
            "Payment Request",
            filters={
                "is_manual_payment": 1,
                "created_by": current_user
            },
            fields=[
                "name", "title", "payment_method", "cart_id", "amount", "total_amount",
                "customer", "customer_name", "status", "approval_status", "created_at", 
                "approved_by", "approved_at", "rejection_reason", "proof_of_payment"
            ],
            order_by="created_at desc",
            limit_start=start,
            limit_page_length=limit
        )

        # Calculate pagination info
        filters = {
            "is_manual_payment": 1,
            "created_by": current_user
        }
        total_count = frappe.db.count("Payment Request", filters)
        current_page = (start // limit) + 1 if limit > 0 else 1
        total_pages = (total_count + limit - 1) // limit if limit > 0 else 1

        return {
            "success": True,
            "manual_payments": manual_payments,
            "pagination": {
                "current_page": current_page,
                "total_pages": total_pages,
                "limit": limit,
                "start": start,
                "has_next": start + limit < total_count,
                "has_previous": start > 0,
                "total_records": total_count
            }
        }

    except Exception as e:
        frappe.log_error(f"Failed to get user manual payments: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=True)
@jwt_required()
def create_payment_request(cart_id, payment_method, **kwargs):
    """Create a payment request for cart items"""
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.local.response["http_status_code"] = 401
            frappe.throw("Authentication required", frappe.AuthenticationError)
        
        # Validate cart exists and is owned by current user or user is administrator
        cart = frappe.get_doc("Tradeline Cart", cart_id)
        if cart.user_id != current_user and current_user != "Administrator" and "Administrator" not in frappe.get_roles(current_user):
            frappe.local.response["http_status_code"] = 403
            frappe.throw(_("Unauthorized access to cart"))

        if cart.status != "Active":
            frappe.local.response["http_status_code"] = 400
            frappe.throw(_("Cart is not active"))

        # Get payment configuration
        payment_config = frappe.get_doc("Payment Configuration", {
            "payment_method": payment_method,
            "is_active": 1
        })

        if not payment_config:
            frappe.local.response["http_status_code"] = 400
            frappe.throw(_("Payment method not configured"))

        # Calculate total amount with fees
        cart_total = cart.calculate_totals()
        fees = payment_config.calculate_fees(cart_total["total"])
        total_amount = cart_total["total"] + fees["total_fee"]

        # Validate amount limits
        if total_amount < payment_config.min_amount:
            frappe.local.response["http_status_code"] = 400
            frappe.throw(_("Amount below minimum limit of ${0}").format(payment_config.min_amount))

        if total_amount > payment_config.max_amount:
            frappe.local.response["http_status_code"] = 400
            frappe.throw(_("Amount exceeds maximum limit of ${0}").format(payment_config.max_amount))

        # Create payment request using configuration
        payment_request = payment_config.create_payment_request(
            amount=cart_total["total"],
            customer_email=kwargs.get("customer_email", current_user),
            description=f"Payment for cart {cart_id}",
            reference_id=cart_id
        )

        # Create Payment Request document
        payment_doc = frappe.get_doc({
            "doctype": "Payment Request",
            "payment_method": payment_method,
            "cart_id": cart_id,
            "amount": cart_total["total"],
            "fees": fees["total_fee"],
            "total_amount": total_amount,
            "customer_email": kwargs.get("customer_email", current_user),
            "payment_data": json.dumps(payment_request),
            "status": "Pending",
            "created_by": current_user,
            "reference_doctype": "Tradeline Cart",
            "reference_name": cart_id
        })

        payment_doc.insert(ignore_permissions=True)

        return {
            "success": True,
            "payment_request_id": payment_doc.name,
            "payment_data": payment_request,
            "total_amount": total_amount,
            "fees": fees
        }

    except Exception as e:
        frappe.log_error(f"Payment request creation failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=True)
@jwt_required()
def process_payment(payment_request_id, **payment_data):
    """Process a payment for cart items"""
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.local.response["http_status_code"] = 401
            frappe.throw("Authentication required", frappe.AuthenticationError)
        
        # Get payment request
        payment_req = frappe.get_doc("Payment Request", payment_request_id)

        if payment_req.status != "Pending":
            frappe.local.response["http_status_code"] = 400
            frappe.throw(_("Payment request is not pending"))

        # Get cart and validate ownership or admin access
        cart = frappe.get_doc("Tradeline Cart", payment_req.cart_id)
        if cart.user_id != current_user and current_user != "Administrator" and "Administrator" not in frappe.get_roles(current_user):
            frappe.local.response["http_status_code"] = 403
            frappe.throw(_("Unauthorized access"))

        # Get payment configuration
        payment_config = frappe.get_doc("Payment Configuration", {
            "payment_method": payment_req.payment_method,
            "is_active": 1
        })

        # Process payment based on method
        if payment_req.payment_method == "PayPal":
            result = _process_paypal_payment(payment_req, payment_config, payment_data)
        elif payment_req.payment_method in ["Apple Cash", "Zelle", "CashApp", "Venmo"]:
            result = _process_p2p_payment(payment_req, payment_config, payment_data)
        else:
            frappe.local.response["http_status_code"] = 400
            frappe.throw(_("Payment method not supported"))

        if result["success"]:
            # Update payment request status
            payment_req.status = "Completed"
            payment_req.transaction_id = result.get("transaction_id")
            payment_req.payment_response = json.dumps(result)
            payment_req.completed_at = now_datetime()
            payment_req.save(ignore_permissions=True)

            # Process cart checkout
            checkout_result = cart.checkout()

            # Create payment entry
            payment_entry = frappe.get_doc({
                "doctype": "Payment Entry",
                "payment_type": "Receive",
                "party_type": "Customer",
                "party": cart.user_id,
                "paid_amount": payment_req.total_amount,
                "received_amount": payment_req.total_amount,
                "reference_no": result.get("transaction_id"),
                "reference_date": now_datetime(),
                "remarks": f"Payment for cart {cart.name} via {payment_req.payment_method}"
            })
            payment_entry.insert(ignore_permissions=True)
            payment_entry.submit()

            return {
                "success": True,
                "transaction_id": result.get("transaction_id"),
                "payment_entry": payment_entry.name,
                "checkout_result": checkout_result
            }
        else:
            # Update payment request with failure
            payment_req.status = "Failed"
            payment_req.payment_response = json.dumps(result)
            payment_req.save(ignore_permissions=True)

            return {
                "success": False,
                "error": result.get("error", "Payment processing failed")
            }

    except Exception as e:
        frappe.log_error(f"Payment processing failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


def _process_paypal_payment(payment_req, config, payment_data):
    """Process PayPal payment"""
    try:
        # In a real implementation, you would integrate with PayPal API
        # For now, we'll simulate the process

        order_id = payment_data.get("order_id")
        if not order_id:
            return {"success": False, "error": "PayPal order ID required"}

        # Simulate PayPal order verification
        # In reality, you would call PayPal's API to verify the order

        return {
            "success": True,
            "transaction_id": f"PAYPAL_{order_id}",
            "payment_method": "PayPal",
            "amount": payment_req.total_amount
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def _process_p2p_payment(payment_req, config, payment_data):
    """Process peer-to-peer payment (Apple Cash, Zelle, CashApp, Venmo)"""
    try:
        payment_method = payment_req.payment_method
        
        # Route to specific payment processor
        if payment_method == "Apple Cash":
            return _process_apple_cash_payment(payment_req, config, payment_data)
        elif payment_method == "Zelle":
            return _process_zelle_payment(payment_req, config, payment_data)
        elif payment_method == "CashApp":
            return _process_cashapp_payment(payment_req, config, payment_data)
        elif payment_method == "Venmo":
            return _process_venmo_payment(payment_req, config, payment_data)
        else:
            return {"success": False, "error": f"Unsupported P2P payment method: {payment_method}"}

    except Exception as e:
        frappe.log_error(f"P2P payment processing error: {str(e)}")
        return {"success": False, "error": str(e)}


def _process_apple_cash_payment(payment_req, config, payment_data):
    """Process Apple Cash payment"""
    try:
        # Required fields for Apple Cash
        transaction_ref = payment_data.get("transaction_reference")
        sender_phone = payment_data.get("sender_phone")
        recipient_phone = payment_data.get("recipient_phone")
        
        if not transaction_ref:
            return {"success": False, "error": "Apple Cash transaction reference required"}
        
        if not sender_phone:
            return {"success": False, "error": "Sender phone number required for Apple Cash"}
            
        # Validate phone number format (basic validation)
        import re
        phone_pattern = r'^\+?[\d\s\-\(\)]{10,15}$'
        if not re.match(phone_pattern, sender_phone):
            return {"success": False, "error": "Invalid sender phone number format"}
        
        # Generate transaction ID
        transaction_id = f"APPLECASH_{transaction_ref}_{now_datetime().strftime('%Y%m%d%H%M%S')}"
        
        # Create verification entry
        _create_payment_verification_entry(payment_req, transaction_id, {
            "transaction_reference": transaction_ref,
            "sender_phone": sender_phone,
            "recipient_phone": recipient_phone,
            "verification_method": "manual",
            "instructions": "Please verify Apple Cash transaction in your Apple Wallet"
        })
        
        return {
            "success": True,
            "transaction_id": transaction_id,
            "payment_method": "Apple Cash",
            "amount": payment_req.total_amount,
            "requires_verification": True,
            "verification_instructions": "Payment verification required. Check your Apple Wallet for the transaction.",
            "next_steps": [
                "Screenshot the Apple Cash transaction",
                "Contact support with transaction reference",
                "Payment will be verified within 24 hours"
            ]
        }
        
    except Exception as e:
        frappe.log_error(f"Apple Cash payment processing error: {str(e)}")
        return {"success": False, "error": str(e)}


def _process_zelle_payment(payment_req, config, payment_data):
    """Process Zelle payment"""
    try:
        # Required fields for Zelle
        transaction_ref = payment_data.get("transaction_reference")
        sender_email = payment_data.get("sender_email")
        sender_phone = payment_data.get("sender_phone")
        recipient_email = payment_data.get("recipient_email")
        
        if not transaction_ref:
            return {"success": False, "error": "Zelle transaction reference required"}
            
        if not sender_email and not sender_phone:
            return {"success": False, "error": "Sender email or phone number required for Zelle"}
            
        # Validate email format if provided
        if sender_email:
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, sender_email):
                return {"success": False, "error": "Invalid sender email format"}
        
        # Generate transaction ID
        transaction_id = f"ZELLE_{transaction_ref}_{now_datetime().strftime('%Y%m%d%H%M%S')}"
        
        # Create verification entry
        _create_payment_verification_entry(payment_req, transaction_id, {
            "transaction_reference": transaction_ref,
            "sender_email": sender_email,
            "sender_phone": sender_phone,
            "recipient_email": recipient_email,
            "verification_method": "email_confirmation",
            "instructions": "Zelle confirmation email will be sent to verify payment"
        })
        
        # Send notification for Zelle verification
        _send_zelle_verification_notification(payment_req, transaction_id, sender_email or sender_phone)
        
        return {
            "success": True,
            "transaction_id": transaction_id,
            "payment_method": "Zelle",
            "amount": payment_req.total_amount,
            "requires_verification": True,
            "verification_instructions": "Please check your email for Zelle payment confirmation.",
            "next_steps": [
                "Check your bank's Zelle confirmation",
                "Forward confirmation email to our support",
                "Payment typically verifies within 1-2 hours"
            ]
        }
        
    except Exception as e:
        frappe.log_error(f"Zelle payment processing error: {str(e)}")
        return {"success": False, "error": str(e)}


def _process_cashapp_payment(payment_req, config, payment_data):
    """Process CashApp payment"""
    try:
        # Required fields for CashApp
        transaction_ref = payment_data.get("transaction_reference")
        cashtag = payment_data.get("cashtag")  # $username format
        recipient_cashtag = payment_data.get("recipient_cashtag")
        
        if not transaction_ref:
            return {"success": False, "error": "CashApp transaction reference required"}
            
        if not cashtag:
            return {"success": False, "error": "Sender CashApp $cashtag required"}
            
        # Validate cashtag format
        import re
        cashtag_pattern = r'^\$[a-zA-Z0-9_]{1,20}$'
        if not re.match(cashtag_pattern, cashtag):
            return {"success": False, "error": "Invalid CashApp $cashtag format (should be $username)"}
        
        # Generate transaction ID
        transaction_id = f"CASHAPP_{transaction_ref}_{now_datetime().strftime('%Y%m%d%H%M%S')}"
        
        # Create verification entry
        _create_payment_verification_entry(payment_req, transaction_id, {
            "transaction_reference": transaction_ref,
            "sender_cashtag": cashtag,
            "recipient_cashtag": recipient_cashtag,
            "verification_method": "screenshot_verification",
            "instructions": "Screenshot of CashApp payment required for verification"
        })
        
        return {
            "success": True,
            "transaction_id": transaction_id,
            "payment_method": "CashApp",
            "amount": payment_req.total_amount,
            "requires_verification": True,
            "verification_instructions": "Please provide screenshot of your CashApp payment.",
            "next_steps": [
                "Take screenshot of CashApp payment confirmation",
                "Upload screenshot through our verification portal",
                "Include transaction reference in the upload",
                "Payment typically verifies within 30 minutes"
            ]
        }
        
    except Exception as e:
        frappe.log_error(f"CashApp payment processing error: {str(e)}")
        return {"success": False, "error": str(e)}


def _process_venmo_payment(payment_req, config, payment_data):
    """Process Venmo payment"""
    try:
        # Required fields for Venmo
        transaction_ref = payment_data.get("transaction_reference")
        username = payment_data.get("username")  # @username format
        recipient_username = payment_data.get("recipient_username")
        note = payment_data.get("note", "")
        
        if not transaction_ref:
            return {"success": False, "error": "Venmo transaction reference required"}
            
        if not username:
            return {"success": False, "error": "Sender Venmo username required"}
            
        # Validate username format
        import re
        username_pattern = r'^@?[a-zA-Z0-9_-]{1,30}$'
        clean_username = username.lstrip('@')
        if not re.match(username_pattern, clean_username):
            return {"success": False, "error": "Invalid Venmo username format"}
        
        # Ensure username has @ prefix
        if not username.startswith('@'):
            username = f"@{username}"
            
        # Generate transaction ID
        transaction_id = f"VENMO_{transaction_ref}_{now_datetime().strftime('%Y%m%d%H%M%S')}"
        
        # Create verification entry
        _create_payment_verification_entry(payment_req, transaction_id, {
            "transaction_reference": transaction_ref,
            "sender_username": username,
            "recipient_username": recipient_username,
            "payment_note": note,
            "verification_method": "activity_feed_check",
            "instructions": "Venmo payment will be verified through activity feed"
        })
        
        return {
            "success": True,
            "transaction_id": transaction_id,
            "payment_method": "Venmo",
            "amount": payment_req.total_amount,
            "requires_verification": True,
            "verification_instructions": "Your Venmo payment is being verified through our secure process.",
            "next_steps": [
                "Ensure payment is visible in your Venmo activity",
                "Keep transaction reference for your records",
                "Payment typically verifies within 15-30 minutes",
                "You may be contacted if additional verification is needed"
            ]
        }
        
    except Exception as e:
        frappe.log_error(f"Venmo payment processing error: {str(e)}")
        return {"success": False, "error": str(e)}


def _create_payment_verification_entry(payment_req, transaction_id, verification_data):
    """Create a payment verification entry for tracking"""
    try:
        verification_doc = frappe.get_doc({
            "doctype": "Payment Verification",
            "payment_request": payment_req.name,
            "transaction_id": transaction_id,
            "payment_method": payment_req.payment_method,
            "amount": payment_req.total_amount,
            "verification_data": json.dumps(verification_data),
            "status": "Pending",
            "created_at": now_datetime(),
            "verification_method": verification_data.get("verification_method", "manual")
        })
        
        verification_doc.insert(ignore_permissions=True)
        return verification_doc.name
        
    except Exception as e:
        frappe.log_error(f"Failed to create payment verification entry: {str(e)}")
        return None


def _send_zelle_verification_notification(payment_req, transaction_id, contact_info):
    """Send Zelle verification notification"""
    try:
        # In a real implementation, you would send an email or SMS
        # For now, we'll log the notification request
        
        notification_data = {
            "type": "zelle_verification",
            "payment_request": payment_req.name,
            "transaction_id": transaction_id,
            "contact_info": contact_info,
            "amount": payment_req.total_amount,
            "timestamp": now_datetime()
        }
        
        frappe.log_error(f"Zelle verification notification: {json.dumps(notification_data)}", "Zelle Verification")
        
        # TODO: Implement actual email/SMS sending
        # send_email(
        #     recipients=[contact_info],
        #     subject="Zelle Payment Verification Required",
        #     message=f"Please confirm your Zelle payment of ${payment_req.total_amount}"
        # )
        
        return True
        
    except Exception as e:
        frappe.log_error(f"Failed to send Zelle verification notification: {str(e)}")
        return False


@frappe.whitelist(allow_guest=True)
@jwt_required()
def verify_p2p_payment(payment_request_id, verification_data=None):
    """Verify P2P payment with additional data"""
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.local.response["http_status_code"] = 401
            frappe.throw("Authentication required", frappe.AuthenticationError)
        
        payment_req = frappe.get_doc("Payment Request", payment_request_id)
        
        # Check permissions
        if current_user != "Administrator" and not frappe.has_permission("Payment Request", "write"):
            frappe.local.response["http_status_code"] = 403
            frappe.throw(_("Insufficient permissions to verify payment"))
        
        # Get verification entry if exists
        verification_entries = frappe.get_all(
            "Payment Verification",
            filters={"payment_request": payment_request_id},
            fields=["name", "status", "verification_data"]
        )
        
        if verification_entries:
            verification_entry = frappe.get_doc("Payment Verification", verification_entries[0]["name"])
            verification_entry.status = "Verified"
            verification_entry.verified_by = current_user
            verification_entry.verified_at = now_datetime()
            
            if verification_data:
                verification_entry.verification_response = json.dumps(verification_data)
            
            verification_entry.save(ignore_permissions=True)
        
        # Update payment request
        payment_req.status = "Verified"
        payment_req.verified_by = current_user
        payment_req.verified_at = now_datetime()
        payment_req.save(ignore_permissions=True)
        
        # Send verification confirmation
        _send_payment_verification_confirmation(payment_req)
        
        return {
            "success": True,
            "message": f"{payment_req.payment_method} payment verified successfully"
        }
        
    except Exception as e:
        frappe.log_error(f"P2P payment verification failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_p2p_payment_status(payment_request_id):
    """Get detailed status of P2P payment"""
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.local.response["http_status_code"] = 401
            frappe.throw("Authentication required", frappe.AuthenticationError)
        
        payment_req = frappe.get_doc("Payment Request", payment_request_id)
        
        # Get verification entries
        verification_entries = frappe.get_all(
            "Payment Verification",
            filters={"payment_request": payment_request_id},
            fields=["name", "status", "verification_method", "created_at", "verified_at"]
        )
        
        status_info = {
            "payment_request_id": payment_request_id,
            "payment_method": payment_req.payment_method,
            "amount": payment_req.total_amount,
            "status": payment_req.status,
            "created_at": payment_req.creation,
            "verification_entries": verification_entries
        }
        
        # Add method-specific status information
        if payment_req.payment_method == "Apple Cash":
            status_info["verification_notes"] = "Apple Cash payments require manual verification through Apple Wallet screenshots"
        elif payment_req.payment_method == "Zelle":
            status_info["verification_notes"] = "Zelle payments are verified through bank confirmation emails"
        elif payment_req.payment_method == "CashApp":
            status_info["verification_notes"] = "CashApp payments require screenshot verification"
        elif payment_req.payment_method == "Venmo":
            status_info["verification_notes"] = "Venmo payments are verified through activity feed checks"
        
        return {
            "success": True,
            "status_info": status_info
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_p2p_payment_instructions(payment_method):
    """Get detailed instructions for P2P payment methods"""
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.local.response["http_status_code"] = 401
            frappe.throw("Authentication required", frappe.AuthenticationError)
        
        instructions = {
            "Apple Cash": {
                "title": "Apple Cash Payment Instructions",
                "steps": [
                    "Open Apple Wallet or Messages app",
                    "Send payment using Apple Cash to the provided recipient",
                    "Note the transaction reference number",
                    "Provide your phone number and transaction reference",
                    "Take screenshot for verification if requested"
                ],
                "required_fields": ["transaction_reference", "sender_phone"],
                "optional_fields": ["recipient_phone"],
                "verification_time": "24 hours",
                "notes": "Apple Cash payments require iOS device and Apple ID"
            },
            "Zelle": {
                "title": "Zelle Payment Instructions", 
                "steps": [
                    "Open your bank's mobile app or online banking",
                    "Go to Zelle section",
                    "Send payment to the provided email or phone",
                    "Note the confirmation number",
                    "Forward bank confirmation email to our support",
                    "Provide transaction reference and sender details"
                ],
                "required_fields": ["transaction_reference", "sender_email or sender_phone"],
                "optional_fields": ["recipient_email"],
                "verification_time": "1-2 hours",
                "notes": "Zelle requires enrollment with participating bank"
            },
            "CashApp": {
                "title": "CashApp Payment Instructions",
                "steps": [
                    "Open Cash App on your mobile device",
                    "Tap Pay tab and enter recipient $cashtag",
                    "Enter payment amount and add note if needed",
                    "Complete payment with PIN or Touch ID",
                    "Screenshot the payment confirmation",
                    "Upload screenshot through verification portal"
                ],
                "required_fields": ["transaction_reference", "cashtag"],
                "optional_fields": ["recipient_cashtag"],
                "verification_time": "30 minutes",
                "notes": "CashApp requires mobile app and verified account"
            },
            "Venmo": {
                "title": "Venmo Payment Instructions",
                "steps": [
                    "Open Venmo mobile app",
                    "Search for recipient username",
                    "Enter payment amount and optional note",
                    "Set privacy to Private (recommended)",
                    "Complete payment",
                    "Note transaction reference from activity feed"
                ],
                "required_fields": ["transaction_reference", "username"],
                "optional_fields": ["recipient_username", "note"],
                "verification_time": "15-30 minutes",
                "notes": "Venmo requires mobile app and connected bank account"
            }
        }
        
        if payment_method not in instructions:
            return {
                "success": False,
                "error": f"Instructions not available for {payment_method}"
            }
        
        return {
            "success": True,
            "instructions": instructions[payment_method]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def _send_payment_verification_confirmation(payment_req):
    """Send payment verification confirmation"""
    try:
        # In a real implementation, send email/SMS to customer
        confirmation_data = {
            "type": "payment_verified",
            "payment_request": payment_req.name,
            "payment_method": payment_req.payment_method,
            "amount": payment_req.total_amount,
            "timestamp": now_datetime()
        }
        
        frappe.log_error(f"Payment verification confirmation: {json.dumps(confirmation_data)}", "Payment Verified")
        
        # TODO: Implement actual notification sending
        return True
        
    except Exception as e:
        frappe.log_error(f"Failed to send verification confirmation: {str(e)}")
        return False


@frappe.whitelist(allow_guest=True)
@jwt_required()
def get_payment_methods():
    """Get all active payment methods"""
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.local.response["http_status_code"] = 401
            frappe.throw("Authentication required", frappe.AuthenticationError)
        
        payment_configs = frappe.get_all(
            "Payment Configuration",
            filters={"is_active": 1},
            fields=[
                "name", "payment_method", "payment_type", "min_amount", 
                "max_amount", "fixed_fee", "percentage_fee", "instructions",
                "icon", "display_name"
            ],
            order_by="creation desc"
        )

        return {
            "success": True,
            "payment_methods": payment_configs
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=True)
@jwt_required()
def calculate_payment_fees(amount, payment_method):
    """Calculate fees for a payment amount and method"""
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.local.response["http_status_code"] = 401
            frappe.throw("Authentication required", frappe.AuthenticationError)
        
        payment_config = frappe.get_doc("Payment Configuration", {
            "payment_method": payment_method,
            "is_active": 1
        })

        if not payment_config:
            frappe.local.response["http_status_code"] = 404
            frappe.throw(_("Payment method not found"))

        fees = payment_config.calculate_fees(flt(amount))

        return {
            "success": True,
            "fees": fees,
            "total_amount": flt(amount) + fees["total_fee"]
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=True)
@jwt_required()
def verify_payment(payment_request_id):
    """Verify payment status (for manual verification)"""
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.local.response["http_status_code"] = 401
            frappe.throw("Authentication required", frappe.AuthenticationError)
        
        payment_req = frappe.get_doc("Payment Request", payment_request_id)
        if current_user != "Administrator" and not frappe.has_permission("Payment Request", "write"):
            frappe.local.response["http_status_code"] = 403
            frappe.throw(_("Insufficient permissions to verify payment"))

        payment_req.status = "Verified"
        payment_req.verified_by = current_user
        payment_req.verified_at = now_datetime()
        payment_req.save(ignore_permissions=True)

        return {
            "success": True,
            "message": "Payment verified successfully"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=True)
@jwt_required()
def test_payment_configuration(payment_method, test_amount=100):
    """Test payment configuration"""
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.local.response["http_status_code"] = 401
            frappe.throw("Authentication required", frappe.AuthenticationError)
        
        payment_config = frappe.get_doc("Payment Configuration", {
            "payment_method": payment_method,
            "is_active": 1
        })

        if not payment_config:
            return {
                "success": False,
                "error": "Payment configuration not found"
            }

        # Validate configuration
        validation_result = payment_config.validate_configuration()
        if not validation_result["valid"]:
            return {
                "success": False,
                "error": f"Configuration validation failed: {validation_result['errors']}"
            }

        # Test fee calculation
        fees = payment_config.calculate_fees(test_amount)

        # Test payment request creation (dry run)
        test_request = payment_config.create_payment_request(
            amount=test_amount,
            customer_email="test@example.com",
            description="Test payment",
            reference_id="TEST"
        )

        return {
            "success": True,
            "message": f"Configuration test successful for {payment_method}",
            "fees": fees,
            "test_request": test_request
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=True)
@jwt_required()
def create_sample_payment(payment_method, amount, customer_email):
    """Create a sample payment request for testing"""
    try:
        current_user = get_authenticated_user()
        if not current_user or current_user == "Guest":
            frappe.local.response["http_status_code"] = 401
            frappe.throw("Authentication required", frappe.AuthenticationError)
        
        payment_config = frappe.get_doc("Payment Configuration", {
            "payment_method": payment_method,
            "is_active": 1
        })

        if not payment_config:
            return {
                "success": False,
                "error": "Payment configuration not found"
            }

        payment_request = payment_config.create_payment_request(
            amount=flt(amount),
            customer_email=customer_email,
            description=f"Sample payment for {payment_method}",
            reference_id="SAMPLE"
        )

        return {
            "success": True,
            "payment_request": payment_request
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

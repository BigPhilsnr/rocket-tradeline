import frappe
from frappe import _
from frappe.utils import flt, now_datetime
from decimal import Decimal
import json
from .auth import jwt_required, get_current_user


@frappe.whitelist()
def create_payment_request(cart_id, payment_method, **kwargs):
    """Create a payment request for cart items"""
    try:
        # Validate cart exists and is owned by current user
        cart = frappe.get_doc("TradelineCart", cart_id)
        current_user = get_current_user()
        if cart.user_id != current_user:
            frappe.throw(_("Unauthorized access to cart"))

        if cart.status != "Active":
            frappe.throw(_("Cart is not active"))

        # Get payment configuration
        payment_config = frappe.get_doc("Payment Configuration", {
            "payment_method": payment_method,
            "is_active": 1
        })

        if not payment_config:
            frappe.throw(_("Payment method not configured"))

        # Calculate total amount with fees
        cart_total = cart.calculate_totals()
        fees = payment_config.calculate_fees(cart_total["total"])
        total_amount = cart_total["total"] + fees["total_fee"]

        # Validate amount limits
        if total_amount < payment_config.min_amount:
            frappe.throw(_("Amount below minimum limit of ${0}").format(payment_config.min_amount))

        if total_amount > payment_config.max_amount:
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
            "reference_doctype": "TradelineCart",
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


@frappe.whitelist()
def process_payment(payment_request_id, **payment_data):
    """Process a payment for cart items"""
    try:
        # Get payment request
        payment_req = frappe.get_doc("Payment Request", payment_request_id)

        if payment_req.status != "Pending":
            frappe.throw(_("Payment request is not pending"))

        # Get cart and validate ownership
        cart = frappe.get_doc("TradelineCart", payment_req.cart_id)
        current_user = get_current_user()
        if cart.user_id != current_user:
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
        # For P2P payments, we typically just verify the payment details
        # The actual transfer is done outside our system

        transaction_ref = payment_data.get("transaction_reference")
        if not transaction_ref:
            return {"success": False, "error": "Transaction reference required"}

        # In a real implementation, you might:
        # 1. Send notifications to verify payment
        # 2. Check with payment provider APIs if available
        # 3. Manual verification process

        return {
            "success": True,
            "transaction_id": f"{payment_req.payment_method.upper()}_{transaction_ref}",
            "payment_method": payment_req.payment_method,
            "amount": payment_req.total_amount,
            "requires_verification": True
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_payment_methods():
    """Get all active payment methods"""
    try:
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


@frappe.whitelist()
def calculate_payment_fees(amount, payment_method):
    """Calculate fees for a payment amount and method"""
    try:
        payment_config = frappe.get_doc("Payment Configuration", {
            "payment_method": payment_method,
            "is_active": 1
        })

        if not payment_config:
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


@frappe.whitelist()
def verify_payment(payment_request_id):
    """Verify payment status (for manual verification)"""
    try:
        payment_req = frappe.get_doc("Payment Request", payment_request_id)
        current_user = get_current_user()
        if current_user != "Administrator" and not frappe.has_permission("Payment Request", "write"):
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


@frappe.whitelist()
def test_payment_configuration(payment_method, test_amount=100):
    """Test payment configuration"""
    try:
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


@frappe.whitelist()
def create_sample_payment(payment_method, amount, customer_email):
    """Create a sample payment request for testing"""
    try:
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

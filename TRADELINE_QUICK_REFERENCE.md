# RocketTradeLine - Quick Reference Guide

## 📋 Purchase Flow Summary

### The 7-Stage Journey

```
1. CREATE CART → 2. ADD ITEMS → 3. CHECKOUT → 4. PAYMENT → 5. APPROVAL → 6. AU ASSIGNMENT → 7. ACTIVE ✅
```

---

## 🔑 Key API Endpoints

### Cart Management (api/cart.py)
| Endpoint | Purpose | Input | Output |
|----------|---------|-------|--------|
| `create_cart()` | Create new shopping cart | - | Cart object |
| `add_to_cart()` | Add tradeline to cart | tradeline_id, quantity | Updated cart |
| `checkout_cart()` | Process checkout | cart_id, address_id | Checkout confirmation |

### Payment (api/payment.py)
| Endpoint | Purpose | Input | Output |
|----------|---------|-------|--------|
| `create_manual_payment_request()` | Create payment with proof | cart_id, payment_method, file | Payment Request ID |
| `upload_payment_proof()` | Add proof later | payment_request_id, file | Upload confirmation |

---

## 📎 Required Attachments

### 1. Proof of Payment
- **When**: During payment request creation
- **Who**: Customer
- **Format**: Image (JPG/PNG) or PDF
- **Attached to**: Payment Request doctype
- **Field**: `proof_of_payment`

### 2. Proof of AU Assignment
- **When**: After cardholder adds AU
- **Who**: Admin (after receiving from cardholder)
- **Format**: Screenshot or PDF from bank
- **Attached to**: Client Tradelines doctype
- **Field**: `proof_of_au_assignment`

---

## ⚡ Status Progressions

### Cart
```
Active → Checked Out → (becomes Payment Request)
```

### Payment Request
```
Pending → Approved → Completed
         ↓
    (Creates Client Tradelines)
```

### Client Tradelines
```
Pending AU ⏸ → Active ✅ → Completed
                  ↓
            (60 days typical duration)
```

---

## ✅ Critical Validations

### Checkout Validations
- [ ] User account is enabled
- [ ] Customer has signed agreement
- [ ] Customer has filled questionnaire
- [ ] Cart has items
- [ ] Payment mode selected
- [ ] **Real-time slot availability check**

### Slot Availability Formula
```python
remaining_spots = max_spots - SUM(active_client_tradelines.quantity)

# Includes statuses: Active, Inactive, Pending AU, Refund Requested
```

---

## 📧 Email Notifications

| Stage | To | Template | Trigger |
|-------|----|----|---------|
| Payment Created | Admin | "Payment Request Notification" | Payment Request insert |
| Payment Approved | Broker/Customer | "Broker Action Required" | approval_status = "Approved" |
| AU Needed | Cardholder | "AU Assignment Notification" | status = "Pending AU" |
| Tradeline Active | Customer/Broker | "Active Status Notification" | status = "Active" |
| Refund Requested | Admin | "Refund Request Notification" | status = "Refund Requested" |

---

## 🔄 Auto-Triggered Hooks

### Payment Request (payment_request.py)

```python
before_insert():
    - validate_unique_cart_id()
    - calculate_fees_from_config()
    - set_customer_info()

on_update():
    - handle_status_change()
      └─ If "Completed" or "Approved": create_client_tradelines()
```

### Client Tradelines (client_tradelines.py)

```python
before_insert():
    - Set default title
    - Set customer_name
    - Set tradeline_name
    - Calculate total_amount

after_insert():
    - recalculate_tradeline_remaining_spots()

on_update():
    - handle_status_change()
      ├─ "Pending AU" → send_au_assignment_email()
      ├─ "Active" → send_active_status_notification_email()
      ├─ "Refund Requested" → send_refund_request_notification_email()
      └─ "Removed" → send_removal_confirmation_email()
```

---

## 🎯 Data Flow

```
Customer
  └─→ Tradeline Cart
       ├─→ items[] (Tradeline Cart Item child table)
       │   ├─ tradeline
       │   ├─ quantity
       │   ├─ rate
       │   └─ amount
       │
       └─→ Payment Request
            ├─ proof_of_payment 📎
            ├─ status: Pending → Completed
            ├─ approval_status: Pending Approval → Approved
            │
            └─→ Client Tradelines (one per cart item)
                 ├─ proof_of_au_assignment 📎
                 ├─ quantity (from cart item)
                 ├─ unit_price (from cart item rate)
                 ├─ status: Pending AU → Active
                 │
                 └─→ Updates Parent Tradeline
                      ├─ purchased_spots
                      └─ remaining_spots
```

---

## 🔒 Security Features

### Authentication
- All APIs require JWT token via `@jwt_required()` decorator
- Session user validated for each request

### Authorization
- `verify_cart_access()` checks cart ownership or admin status
- Files marked `is_private=1` for admin-only access
- Customer can only see their own records

### File Uploads
- Stored in File doctype
- Linked via `attached_to_*` fields
- Private files require authentication to access

---

## 💡 Important Notes

### Slot Calculation
- Runs **real-time** at checkout via `validate_cart_slots()`
- Prevents overbooking by checking current database state
- Returns **409 Conflict** if slots unavailable

### Payment Request Uniqueness
- Only **one active payment** allowed per cart
- Validates in `validate_unique_cart_id()`
- Statuses that block new payment: Pending, Completed, Verified

### Tradeline Spot Updates
- Automatically recalculated on Client Tradelines changes
- Updates parent Tradeline's `purchased_spots` and `remaining_spots`
- Triggered by: insert, update (quantity/status), delete

### Email Template System
- Uses Email Template Custom doctype
- Dynamic context variables injected
- Broker routing: sends to `account_manager` if set, else customer

---

## 📊 DocType Fields Summary

### Tradeline Cart
```python
user_id           # Email of cart owner
customer          # Link to Customer
status            # Active, Checked Out, Expired
payment_status    # Pending, Completed
payment_mode      # Link to Mode of Payment
cart_expiry       # Date (30 days default)
subtotal          # Float
discount_amount   # Float
tax_amount        # Float
total_amount      # Float
items             # Child table: Tradeline Cart Item
```

### Payment Request
```python
title             # Auto-generated
payment_method    # From Payment Configuration
cart_id           # Link to Tradeline Cart
customer          # Link to Customer
customer_email    # Email address
amount            # Base amount
fees              # Calculated from config
total_amount      # amount + fees
status            # Pending, Completed, Failed, Expired
approval_status   # Pending Approval, Approved
is_manual_payment # Boolean
proof_of_payment  # File attachment
transaction_id    # String
created_by        # User
created_at        # Datetime
completed_at      # Datetime
expiry_date       # Datetime (24 hours)
```

### Client Tradelines
```python
title             # Auto-generated
customer          # Link to Customer
customer_name     # String
cart              # Link to Tradeline Cart
payment_request   # Link to Payment Request
tradeline         # Link to Tradeline
tradeline_name    # String
quantity          # Integer
unit_price        # Float
total_amount      # Float
status            # Pending AU, Active, Inactive, etc.
created_date      # Date
completion_date   # Date
expiry_date       # Date (60 days typical)
swapped           # Boolean
swapped_on        # Datetime
refund_reason     # Text
```

---

## 🚀 Quick Start Commands

### Create Cart and Add Item
```python
# 1. Create cart
cart_response = create_cart()
cart_id = cart_response['cart_id']

# 2. Add tradeline
add_to_cart(tradeline_id="TL-0001", quantity=1)

# 3. Checkout
checkout_cart(cart_id=cart_id, address_id="ADDR-0001")
```

### Create Payment Request
```python
# Upload proof of payment and create request
create_manual_payment_request(
    cart_id=cart_id,
    payment_method="Bank Transfer",
    # File uploaded via frappe.request.files['proof_of_payment']
)
```

### Admin Approval
```python
# Admin updates via Frappe Desk:
payment_request = frappe.get_doc("Payment Request", "PAY-XXX")
payment_request.approval_status = "Approved"
payment_request.status = "Completed"
payment_request.save()
# This automatically creates Client Tradelines
```

---

## 📞 Contact & Support

**Admin Email**: info@rockettradeline.com  
**Portal**: https://www.rockettradeline.com  
**Documentation**: See TRADELINE_PURCHASE_FLOW.md for complete details

---

## 📁 File Locations

### API Files
- `apps/rockettradeline/rockettradeline/api/cart.py`
- `apps/rockettradeline/rockettradeline/api/payment.py`
- `apps/rockettradeline/rockettradeline/api/client_tradelines.py`

### DocType Files
- `apps/rockettradeline/rockettradeline/rockettradeline/doctype/tradeline_cart/`
- `apps/rockettradeline/rockettradeline/rockettradeline/doctype/payment_request/`
- `apps/rockettradeline/rockettradeline/rockettradeline/doctype/client_tradelines/`

### Templates
- Email templates stored in: Email Template Custom doctype
- Template names:
  - Payment Request Notification
  - Broker Action Required
  - AU Assignment Notification
  - AU Assignment Reminder
  - Active Status Notification
  - Refund Request Notification
  - Removal Confirmation

---

*Last Updated: 2025-10-12*

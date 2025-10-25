# RocketTradeLine - Complete Purchase Flow Documentation

## Overview
This document details the complete customer journey from cart creation to active tradeline, including all attachments and status transitions.

---

## 🔄 Complete Purchase Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TRADELINE PURCHASE FLOW                              │
└─────────────────────────────────────────────────────────────────────────────┘

   STAGE 1: CART CREATION & MANAGEMENT
   ════════════════════════════════════════════════════════════════════════
   
   ┌──────────────┐
   │   Customer   │
   │    Login     │
   └──────┬───────┘
          │
          ▼
   ┌──────────────────────────────────────────────────────────────┐
   │  API: create_cart()                                          │
   │  File: api/cart.py                                           │
   │                                                               │
   │  Checks:                                                      │
   │  • User authentication (JWT token)                           │
   │  • Existing active cart                                      │
   │  • Customer record exists                                    │
   │                                                               │
   │  Creates:                                                     │
   │  • Tradeline Cart (doctype)                                  │
   │    - user_id: current_user                                   │
   │    - customer: linked customer                               │
   │    - status: "Active"                                        │
   │    - cart_expiry: now() + 30 days                            │
   └──────┬───────────────────────────────────────────────────────┘
          │
          ▼
   ┌──────────────────────────────────────────────────────────────┐
   │  API: add_to_cart(tradeline_id, quantity)                   │
   │  File: api/cart.py                                           │
   │                                                               │
   │  Validates:                                                   │
   │  • Tradeline is Active                                       │
   │  • Quantity <= max_spots                                     │
   │  • Slot availability                                         │
   │                                                               │
   │  Updates:                                                     │
   │  • Tradeline Cart Item (child table)                         │
   │    - tradeline: tradeline_id                                 │
   │    - quantity: requested quantity                            │
   │    - rate: tradeline.price                                   │
   │    - amount: quantity × rate                                 │
   │                                                               │
   │  Cart Operations Available:                                   │
   │  • update_cart_item() - modify quantities                    │
   │  • remove_from_cart() - remove items                         │
   │  • clear_cart() - remove all items                           │
   │  • apply_discount() - apply discounts                        │
   └──────┬───────────────────────────────────────────────────────┘
          │
          │
   STAGE 2: CHECKOUT PROCESS
   ════════════════════════════════════════════════════════════════════════
          │
          ▼
   ┌──────────────────────────────────────────────────────────────┐
   │  API: checkout_cart(cart_id, address_id)                    │
   │  File: api/cart.py                                           │
   │                                                               │
   │  Pre-Checkout Validations:                                   │
   │  ├─ User account is enabled                                  │
   │  ├─ Customer has signed agreement                            │
   │  ├─ Questionnaire is filled                                  │
   │  ├─ Cart is not empty                                        │
   │  ├─ Payment mode selected                                    │
   │  ├─ validate_cart_slots() - Real-time slot check            │
   │  │   • Gets all active Client Tradelines                     │
   │  │   • Calculates remaining_spots                            │
   │  │   • Ensures requested quantity available                  │
   │  │   • Returns 409 Conflict if slots exceeded               │
   │  └─ Customer information present                             │
   │                                                               │
   │  Updates Cart:                                                │
   │  • status: "Active" → "Checked Out"                          │
   │  • payment_status: "Pending"                                 │
   │  • payment_address: address_id                               │
   │                                                               │
   │  Response Status Codes:                                       │
   │  • 417: Expectation Failed (user disabled/agreement/quiz)   │
   │  • 409: Conflict (slot availability issues)                  │
   │  • 200: Success                                              │
   └──────┬───────────────────────────────────────────────────────┘
          │
          │
   STAGE 3: PAYMENT REQUEST CREATION
   ════════════════════════════════════════════════════════════════════════
          │
          ▼
   ┌──────────────────────────────────────────────────────────────┐
   │  API: create_manual_payment_request()                       │
   │  File: api/payment.py                                        │
   │                                                               │
   │  Input:                                                       │
   │  • cart_id                                                    │
   │  • payment_method (from Payment Configuration)              │
   │  • proof_of_payment (file upload) 📎 ATTACHMENT #1          │
   │                                                               │
   │  File Upload Process:                                         │
   │  1. Receives file from frappe.request.files                  │
   │  2. Creates File doctype record                              │
   │     - file_name: uploaded_file.filename                      │
   │     - is_private: 1                                          │
   │     - content: file bytes                                    │
   │  3. Links file to Payment Request                            │
   │     - attached_to_doctype: "Payment Request"                │
   │     - attached_to_name: payment_request.name                │
   │     - attached_to_field: "proof_of_payment"                 │
   │                                                               │
   │  Creates:                                                     │
   │  • Payment Request (doctype)                                 │
   │    File: doctype/payment_request/payment_request.py          │
   │                                                               │
   │    Fields:                                                    │
   │    ├─ title: "PAY-{cart_id}-{timestamp}"                    │
   │    ├─ payment_method: selected method                        │
   │    ├─ cart_id: linked cart                                   │
   │    ├─ customer: from cart                                    │
   │    ├─ customer_email: user email                             │
   │    ├─ amount: cart total                                     │
   │    ├─ fees: calculated from Payment Configuration           │
   │    ├─ total_amount: amount + fees                            │
   │    ├─ status: "Pending"                                      │
   │    ├─ approval_status: "Pending Approval"                    │
   │    ├─ is_manual_payment: 1                                   │
   │    ├─ proof_of_payment: file_url 📎                         │
   │    ├─ created_by: current_user                               │
   │    ├─ created_at: now_datetime()                             │
   │    ├─ expiry_date: now() + 24 hours                          │
   │    ├─ reference_doctype: "Tradeline Cart"                   │
   │    └─ reference_name: cart_id                                │
   │                                                               │
   │  Validations (before_insert):                                │
   │  • validate_unique_cart_id() - No active payments exist      │
   │  • calculate_fees_from_config() - Get fees from config       │
   │  • set_customer_info() - Link customer data                  │
   │                                                               │
   │  Email Notifications:                                         │
   │  📧 send_payment_request_notification_email()                │
   │     To: info@rockettradeline.com (Admin)                     │
   │     Template: "Payment Request Notification"                 │
   │     Context:                                                  │
   │     • payment_request_id, customer info                      │
   │     • payment_method, amounts                                │
   │     • cart_id, status                                        │
   └──────┬───────────────────────────────────────────────────────┘
          │
          │
   STAGE 4: PAYMENT APPROVAL (ADMIN ACTION)
   ════════════════════════════════════════════════════════════════════════
          │
          ▼
   ┌──────────────────────────────────────────────────────────────┐
   │  Admin Reviews Payment Request                               │
   │  Location: Frappe Desk → Payment Request                     │
   │                                                               │
   │  Admin Actions:                                               │
   │  1. Views proof_of_payment attachment 📎                     │
   │  2. Verifies payment details                                 │
   │  3. Updates fields:                                           │
   │     • approval_status: "Pending Approval" → "Approved"      │
   │     • status: "Pending" → "Completed"                        │
   │     • completed_at: now_datetime()                           │
   │     • verified_by: admin user                                │
   │                                                               │
   │  Triggers (on_update in payment_request.py):                 │
   │  • handle_status_change()                                    │
   │    └─ When status = "Completed" OR                          │
   │       approval_status = "Approved":                          │
   │       └─ create_client_tradelines()                         │
   │                                                               │
   │  Email Notifications:                                         │
   │  📧 send_payment_approval_email()                            │
   │     File: api/payment.py                                     │
   │     Logic:                                                    │
   │     • Gets cart tradeline details                            │
   │     • Checks customer.account_manager                        │
   │     • If account_manager exists:                             │
   │       ├─ To: customer.account_manager (Broker)              │
   │       ├─ Template: "Broker Action Required"                 │
   │       └─ Notifies broker to add AU                           │
   │     • Else: (Currently disabled per requirements)            │
   │       └─ Would send to customer                              │
   └──────┬───────────────────────────────────────────────────────┘
          │
          │
   STAGE 5: CLIENT TRADELINE CREATION
   ════════════════════════════════════════════════════════════════════════
          │
          ▼
   ┌──────────────────────────────────────────────────────────────┐
   │  Function: create_client_tradelines_from_payment()          │
   │  File: doctype/client_tradelines/client_tradelines.py       │
   │  Triggered by: Payment Request approval                      │
   │                                                               │
   │  Process:                                                     │
   │  FOR EACH cart_item IN cart.items:                           │
   │    ├─ Get tradeline details                                  │
   │    ├─ Get customer info                                      │
   │    └─ Create Client Tradelines record:                       │
   │                                                               │
   │       Client Tradelines (doctype)                            │
   │       ═══════════════════════════════════                    │
   │       • title: "CT-{customer}-{tradeline}-{timestamp}"      │
   │       • customer: from cart                                  │
   │       • customer_name: customer.customer_name                │
   │       • cart: payment_request.cart_id                        │
   │       • payment_request: payment_request.name                │
   │       • tradeline: cart_item.tradeline                       │
   │       • tradeline_name: "{bank} - ${credit_limit}"          │
   │       • quantity: cart_item.quantity                         │
   │       • unit_price: cart_item.rate                           │
   │       • total_amount: cart_item.amount                       │
   │       • status: "Pending AU" ⏸                               │
   │       • created_date: now_datetime()                         │
   │       • notes: "Created from payment {pr_id}"                │
   │                                                               │
   │  Hooks Triggered (before_insert):                            │
   │  • Set default title                                         │
   │  • Set customer_name from Customer                           │
   │  • Set tradeline_name from Tradeline                         │
   │  • Calculate total_amount                                    │
   │                                                               │
   │  Hooks Triggered (after_insert):                             │
   │  • recalculate_tradeline_remaining_spots()                   │
   │    └─ Updates parent Tradeline:                             │
   │       ├─ purchased_spots: sum of all active quantities       │
   │       ├─ remaining_spots: max_spots - purchased_spots       │
   │       └─ Prevents overbooking                                │
   │                                                               │
   │  Status Change Triggers (handle_status_change):              │
   │  • "Pending AU": send_au_assignment_email() 📧              │
   │  • "Active": send_active_status_notification_email() 📧     │
   │  • "Refund Requested": send_refund_request_notification() 📧│
   │  • "Removed": send_removal_confirmation_email() 📧          │
   └──────┬───────────────────────────────────────────────────────┘
          │
          │
   STAGE 6: AU ASSIGNMENT (CARDHOLDER ACTION)
   ════════════════════════════════════════════════════════════════════════
          │
          ▼
   ┌──────────────────────────────────────────────────────────────┐
   │  Status: "Pending AU" ⏸                                      │
   │                                                               │
   │  Email Notification Sent:                                     │
   │  📧 send_au_assignment_email()                               │
   │     File: client_tradelines.py                               │
   │     To: cardholder (tradeline.card_holder.email_id)         │
   │     Template: "AU Assignment Notification"                   │
   │                                                               │
   │     Context Gathered:                                         │
   │     ├─ Cardholder: tradeline.card_holder                    │
   │     ├─ AU Customer: client_tradeline.customer                │
   │     ├─ Bank: tradeline.bank                                  │
   │     └─ Tradeline details                                     │
   │                                                               │
   │     Email Context:                                            │
   │     • cardholder_first_name                                  │
   │     • au_first_name, au_last_initial                         │
   │     • au_dob: MM/DD format (from User.birth_date)           │
   │     • au_ssn_last_4: last 4 of customer.tax_id              │
   │     • year_opened: current_year - tradeline.age_year        │
   │     • bank_name                                              │
   │     • credit_limit: formatted $X,XXX                         │
   │     • closing_date: MM/DD format                             │
   │     • payment_amount: tradeline.commission                   │
   │     • cardholder_login_link                                  │
   │                                                               │
   │  Cardholder Actions Required:                                │
   │  1. Log in to bank account                                   │
   │  2. Add AU (Authorized User) with:                           │
   │     • Customer name                                           │
   │     • Date of birth                                           │
   │     • SSN last 4 digits                                      │
   │  3. Upload proof_of_au_assignment 📎 ATTACHMENT #2          │
   │                                                               │
   │  Admin Updates Client Tradeline:                             │
   │  • Uploads proof_of_au_assignment file                       │
   │  • status: "Pending AU" → "Active" ✅                        │
   │                                                               │
   │  Reminder System:                                             │
   │  📧 send_au_assignment_reminder_email()                      │
   │     Triggered by: Scheduled task (tasks.py)                  │
   │     Frequency: If status = "Pending AU" for > X days         │
   │     Template: "AU Assignment Reminder"                       │
   └──────┬───────────────────────────────────────────────────────┘
          │
          │
   STAGE 7: ACTIVE TRADELINE ✅
   ════════════════════════════════════════════════════════════════════════
          │
          ▼
   ┌──────────────────────────────────────────────────────────────┐
   │  Status: "Active" ✅                                         │
   │                                                               │
   │  Triggers (handle_status_change):                            │
   │  • recalculate_tradeline_remaining_spots()                   │
   │    └─ Ensures parent Tradeline spots are current            │
   │                                                               │
   │  Email Notification Sent:                                     │
   │  📧 send_active_status_notification_email()                  │
   │     File: client_tradelines.py                               │
   │     To: customer OR customer.account_manager (if exists)    │
   │     Template: "Active Status Notification"                   │
   │                                                               │
   │     Email Context:                                            │
   │     • customer_name, customer_first_name                     │
   │     • year_opened: tradeline.age_year                        │
   │     • bank_name                                              │
   │     • credit_limit_k: formatted $XK                          │
   │     • closing_day: tradeline.closing_date day (1st, 2nd...)│
   │     • tradeline_info: Full tradeline details                 │
   │     • mailing_address: tradeline.mailing_address formatted   │
   │                                                               │
   │     Message:                                                  │
   │     "Your tradeline is now active and reporting to          │
   │      credit bureaus. It typically takes 30-60 days to       │
   │      appear on your credit report."                          │
   │                                                               │
   │  Attached Files:                                              │
   │  📎 proof_of_payment (from Payment Request)                  │
   │  📎 proof_of_au_assignment (from Admin)                      │
   │                                                               │
   │  Active Tradeline Features:                                   │
   │  • Visible in customer portal                                │
   │  • Tracks expiry_date (typical: 60 days)                    │
   │  • Can request refund if issues                              │
   │  • Monitors reporting status                                 │
   │  • Swap functionality available (if needed)                  │
   └──────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════
                              STATUS FLOW DIAGRAM
═══════════════════════════════════════════════════════════════════════════

Cart Status Flow:
─────────────────
Active → Checked Out → (Payment Request Created)
   │
   └─→ Expired (if cart_expiry passed)


Payment Request Status Flow:
────────────────────────────
Draft → Pending → Completed → Verified
         │           │
         ├→ Failed   └→ (Creates Client Tradelines)
         ├→ Expired
         ├→ Cancelled
         └→ Refunded

Approval Status: Pending Approval → Approved → (Triggers Client Tradeline creation)


Client Tradelines Status Flow:
──────────────────────────────
Pending AU ⏸ → Active ✅ → Completed / Removed
    │            │
    │            ├→ Inactive
    │            ├→ Refund Requested
    │            └→ Cancelled
    │
    └─→ (Awaiting cardholder AU assignment)


═══════════════════════════════════════════════════════════════════════════
                            ATTACHMENT TRACKING
═══════════════════════════════════════════════════════════════════════════

📎 ATTACHMENT #1: Proof of Payment
────────────────────────────────────
• When: During checkout / payment request creation
• Uploaded by: Customer
• API: create_manual_payment_request()
• Attached to: Payment Request
• Field: proof_of_payment
• File location: File doctype (is_private=1)
• Purpose: Admin verification of payment
• Format: Image (jpg, png) or PDF
• Access: Admin only (private file)


📎 ATTACHMENT #2: Proof of AU Assignment
─────────────────────────────────────────
• When: After cardholder adds AU to bank account
• Uploaded by: Admin (after receiving from cardholder)
• Attached to: Client Tradelines
• Field: proof_of_au_assignment (custom)
• File location: File doctype (is_private=1)
• Purpose: Verify AU was added to account
• Format: Screenshot or PDF from bank
• Access: Admin and linked customer
• Triggers: Status change to "Active"


═══════════════════════════════════════════════════════════════════════════
                          KEY VALIDATION RULES
═══════════════════════════════════════════════════════════════════════════

Cart Checkout Validations:
──────────────────────────
✓ User account enabled
✓ Customer has_signed_agreement = 1
✓ Customer is_questionnaire_filled = 1
✓ Cart has items
✓ Payment mode selected
✓ Customer information present
✓ Real-time slot availability check (validate_cart_slots)


Slot Availability Logic:
────────────────────────
1. For each cart item:
   • Get tradeline.max_spots
   • Query all Client Tradelines with:
     - tradeline = current tradeline
     - status IN ('Active', 'Inactive', 'Pending AU', 'Refund Requested')
   • Sum quantities: total_purchased
   • Calculate: remaining = max_spots - total_purchased
   • Validate: cart_item.quantity <= remaining

2. If any item exceeds available spots:
   • Return 409 Conflict
   • Provide detailed error with:
     - tradeline_name
     - requested quantity
     - available quantity


Payment Request Validations:
────────────────────────────
✓ Cart belongs to user (or user is admin)
✓ No duplicate active payment for cart
✓ Payment method is configured and active
✓ Amount > 0
✓ Fees >= 0
✓ total_amount = amount + fees (±0.01 tolerance)


═══════════════════════════════════════════════════════════════════════════
                        EMAIL NOTIFICATION FLOW
═══════════════════════════════════════════════════════════════════════════

1. Payment Request Created
   📧 To: info@rockettradeline.com (Admin)
   Template: "Payment Request Notification"
   Trigger: Payment Request.after_insert()

2. Payment Approved
   📧 To: customer.account_manager (if exists)
   Template: "Broker Action Required"
   Trigger: Payment Request approval_status → "Approved"
   Purpose: Notify broker to add AU

3. Client Tradeline Created - Pending AU
   📧 To: cardholder_email (tradeline.card_holder.email_id)
   Template: "AU Assignment Notification"
   Trigger: Client Tradelines status → "Pending AU"
   Purpose: Request AU addition with customer details

4. AU Assignment Reminder
   📧 To: cardholder_email
   Template: "AU Assignment Reminder"
   Trigger: Scheduled task (if Pending AU > X days)
   Purpose: Follow-up reminder for AU addition

5. Tradeline Activated
   📧 To: customer_email OR account_manager
   Template: "Active Status Notification"
   Trigger: Client Tradelines status → "Active"
   Purpose: Confirm tradeline is active and reporting

6. Refund Requested
   📧 To: info@rockettradeline.com (Admin)
   Template: "Refund Request Notification"
   Trigger: Client Tradelines status → "Refund Requested"
   Purpose: Alert admin of refund request with details

7. Tradeline Removed
   📧 To: customer_email
   Template: "Removal Confirmation"
   Trigger: Client Tradelines status → "Removed"
   Purpose: Confirm AU removal from account


═══════════════════════════════════════════════════════════════════════════
                            API ENDPOINTS SUMMARY
═══════════════════════════════════════════════════════════════════════════

Cart Management (api/cart.py):
───────────────────────────────
• create_cart() → Create new cart
• get_cart(cart_id) → Get cart details
• add_to_cart(tradeline_id, quantity) → Add item
• update_cart_item(tradeline_id, quantity) → Update quantity
• remove_from_cart(tradeline_id) → Remove item
• clear_cart() → Clear all items
• apply_discount(type, value) → Apply discount
• update_payment_mode(mode) → Set payment method
• checkout_cart(cart_id, address_id) → Process checkout
• get_carts(filters) → List carts (admin)

Payment (api/payment.py):
─────────────────────────
• create_manual_payment_request(cart_id, method) → Create payment with proof
• upload_payment_proof(payment_request_id) → Add proof later
• get_payment_methods() → List available methods
• calculate_payment_fees(amount, method) → Get fee calculation
• process_cart_payment(payment_request_id) → Process payment
• get_cart_payment_status(cart_id) → Check payment status

Client Tradelines (api/client_tradelines.py):
─────────────────────────────────────────────
• get_client_tradelines(filters) → List customer tradelines
• get_client_tradeline(id) → Get details
• update_client_tradeline_status(id, status) → Change status
• request_refund(id, reason) → Request refund
• swap_tradeline(id, new_tradeline_id) → Swap to different tradeline


═══════════════════════════════════════════════════════════════════════════
                        DOCTYPE RELATIONSHIPS
═══════════════════════════════════════════════════════════════════════════

Customer ─────┬──── Tradeline Cart
              │
              ├──── Payment Request
              │
              └──── Client Tradelines
                    │
                    ├──── Tradeline (link)
                    │     │
                    │     ├──── Tradeline Bank (link)
                    │     └──── Card Holder (Customer link)
                    │
                    ├──── Payment Request (link)
                    │
                    └──── Tradeline Cart (link)


Data Flow:
──────────
Tradeline Cart
    ├─→ items[] (Tradeline Cart Item child table)
    │   ├─ tradeline
    │   ├─ quantity
    │   ├─ rate
    │   └─ amount
    │
    └─→ Payment Request
        ├─ proof_of_payment 📎
        └─→ Client Tradelines (multiple, one per cart item)
            ├─ proof_of_au_assignment 📎
            ├─ quantity (from cart item)
            ├─ unit_price (from cart item rate)
            └─ status progression: Pending AU → Active


═══════════════════════════════════════════════════════════════════════════
                          SCHEDULED TASKS
═══════════════════════════════════════════════════════════════════════════

File: tasks.py

1. cleanup_expired_carts()
   Frequency: Daily
   Purpose: Set expired carts to "Expired" status

2. handle_expired_payments()
   Frequency: Hourly
   Purpose: Mark expired payment requests

3. send_au_assignment_reminders()
   Frequency: Daily
   Purpose: Remind cardholders of pending AU assignments

4. check_tradeline_expiry()
   Frequency: Daily
   Purpose: Update Client Tradelines past expiry_date

5. recalculate_all_tradeline_spots()
   Frequency: Daily (maintenance)
   Purpose: Ensure tradeline spot calculations are accurate


═══════════════════════════════════════════════════════════════════════════
                        IMPORTANT NOTES
═══════════════════════════════════════════════════════════════════════════

🔒 Security:
────────────
• All APIs use @jwt_required() decorator
• Files are marked is_private=1 for admin-only access
• verify_cart_access() checks ownership or admin status
• Payment proof required before approval

🔄 Real-Time Validation:
────────────────────────
• validate_cart_slots() runs at checkout to prevent overbooking
• Slot calculation includes: Active, Inactive, Pending AU, Refund Requested
• Uses database-level querying for accuracy

📊 Spot Calculation:
────────────────────
• Triggered on Client Tradelines insert/update/delete
• Updates parent Tradeline in real-time
• Formula: remaining_spots = max_spots - SUM(active client quantities)
• Prevents remaining_spots from going negative

💾 Data Integrity:
──────────────────
• Payment Request validates unique cart_id
• Client Tradelines automatically recalculates parent tradeline spots
• Status transitions trigger appropriate notifications
• Comments added for audit trail

🔔 Notification Logic:
──────────────────────
• Uses Email Template Custom system
• Template variables injected from context
• Sends to appropriate recipient (customer/broker/admin)
• Failure logged but doesn't block process

📎 File Management:
───────────────────
• Files stored in File doctype
• Linked via attached_to_* fields
• Private files require authentication
• Supports multiple file attachments per record


═══════════════════════════════════════════════════════════════════════════

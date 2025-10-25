# Tradeline Bulk Import System - Design Document

## 📋 Overview

This document outlines the design and implementation of a **Tradeline Manual Import** system that allows administrators to manually enter existing tradeline purchase data. The system creates all necessary records (Customer, Cart, Payment Request, Client Tradelines) while maintaining data integrity and bypassing email notifications for external imports.

---

## 🎯 Business Requirements

### Primary Objective
Create a DocType that accepts manual entry of historical tradeline purchases and automatically creates all necessary records in the system without triggering customer/cardholder email notifications.

### Key Features
1. ✅ **Manual Data Entry**: Add import items one by one directly in the form
2. ✅ **Complete Record Creation**: Automatically create Customer → Cart → Payment Request → Client Tradelines
3. ✅ **Attachment Support**: Handle proof of payment and AU assignment attachments
4. ✅ **Discount Support**: Import percentage and fixed-amount discounts
5. ✅ **External Flag System**: Mark imported records as external to suppress emails
6. ✅ **Data Validation**: Ensure data integrity and chronological date validation
7. ✅ **Status Preservation**: Maintain original payment and tradeline statuses

---

## 📊 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                     TRADELINE IMPORT FLOW                           │
└─────────────────────────────────────────────────────────────────────┘

                        ┌─────────────────┐
                        │  Admin Manual   │
                        │  Data Entry     │
                        └────────┬────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │ Tradeline Import       │
                    │ DocType (New)          │
                    │                        │
                    │ Fields:                │
                    │ • Import items (Table) │
                    │ • Import date          │
                    │ • Import status        │
                    │ • Validation log       │
                    └────────┬───────────────┘
                             │ on_save()
                             │
            ┌────────────────┼────────────────┐
            │                │                │
            ▼                ▼                ▼
    ┌───────────────┐  ┌──────────────┐  ┌──────────────┐
    │   Validate    │  │  Create/Link │  │   Process    │
    │   Data        │→ │   Customer   │→ │   Records    │
    │               │  │ (is_external)│  │              │
    └───────────────┘  └──────────────┘  └──────┬───────┘
                                                 │
                        ┌────────────────────────┼────────────────┐
                        │                        │                │
                        ▼                        ▼                ▼
            ┌──────────────────┐   ┌─────────────────────┐   ┌──────────────────┐
            │ Tradeline Cart   │   │  Payment Request    │   │ Client Tradelines│
            │ (is_external=1)  │→  │  (is_external=1)    │→  │ (is_external=1)  │
            │                  │   │                     │   │                  │
            │ • Status         │   │ • Amount            │   │ • Quantity       │
            │ • Items          │   │ • Status            │   │ • Status         │
            │ • Payment mode   │   │ • Approval status   │   │ • Dates          │
            │ • Created date   │   │ • Proof of payment  │   │ • Proof of AU    │
            │ • Discounts      │   │ • Created date      │   │ • Discounts      │
            └──────────────────┘   └─────────────────────┘   └──────────────────┘
                                             │
                                             ▼
                               ┌──────────────────────────┐
                               │  Email Suppression       │
                               │  Check                   │
                               │                          │
                               │  if is_external == 1:    │
                               │     skip email send      │
                               │  else:                   │
                               │     send email normally  │
                               └──────────────────────────┘
```

---

## 🗂️ DocType: Tradeline Import

### DocType Metadata
```json
{
  "name": "Tradeline Import",
  "module": "RocketTradeLine",
  "autoname": "format:IMP-{#####}",
  "is_submittable": 1,
  "track_changes": 1,
  "permissions": [
    {
      "role": "System Manager",
      "create": 1,
      "read": 1,
      "write": 1,
      "delete": 1
    },
    {
      "role": "Administrator",
      "create": 1,
      "read": 1,
      "write": 1,
      "delete": 1
    }
  ]
}
```

### Field Structure

#### Main Fields
| Field Name | Field Type | Label | Description |
|-----------|-----------|-------|-------------|
| `import_title` | Data | Import Title | Title/reference for this import batch |
| `import_date` | Datetime | Import Date | When the import was performed |
| `import_status` | Select | Import Status | Draft, In Progress, Completed, Failed |
| `import_notes` | Text Editor | Import Notes | Admin notes about this import |
| `section_break_items` | Section Break | Import Items | - |
| `import_items` | Table | Import Items | Child table with import data |
| `section_break_summary` | Section Break | Import Summary | - |
| `total_records` | Int | Total Records | Count of import items |
| `successful_imports` | Int | Successful Imports | Count of successful records |
| `failed_imports` | Int | Failed Imports | Count of failed records |
| `column_break_summary` | Column Break | - | - |
| `validation_log` | Text Editor | Validation Log | Errors and warnings |
| `processing_log` | Long Text | Processing Log | Detailed processing information |
| `section_break_settings` | Section Break | Settings | - |
| `suppress_emails` | Check | Suppress Emails | Always suppress emails (default: 1) |

#### Child Table: Tradeline Import Item

| Field Name | Field Type | Label | Required | Description |
|-----------|-----------|-------|----------|-------------|
| **Customer Information** |
| `customer_email` | Data | Customer Email | Yes | Email of the customer |
| `customer_name` | Data | Customer Name | Yes | Full name of customer |
| `customer_phone` | Data | Customer Phone | No | Phone number |
| **Tradeline Details** |
| `tradeline_id` | Link (Tradeline) | Tradeline | Yes | Link to Tradeline DocType |
| `tradeline_name` | Data | Tradeline Name | No | Read-only, fetched from tradeline |
| `quantity` | Int | Quantity | Yes | Number of AU spots purchased |
| `unit_price` | Currency | Unit Price | Yes | Price per spot |
| **Discount Information** |
| `discount_type` | Select | Discount Type | No | Options: Percentage, Amount |
| `discount_value` | Float | Discount Value | No | Percentage (0-100) or amount |
| **Date Tracking** |
| `cart_created_date` | Datetime | Cart Created Date | Yes | When cart was created |
| `payment_approved_date` | Datetime | Payment Approved Date | Yes | When payment was approved |
| `au_added_date` | Datetime | AU Added Date | No | When AU was added to account |
| `expiry_date` | Date | Expiry Date | No | When tradeline expires |
| **Status Fields** |
| `payment_status` | Select | Payment Status | Yes | Payment Request status |
| `approval_status` | Select | Approval Status | Yes | Payment approval status |
| `client_tradeline_status` | Select | Client Tradeline Status | Yes | Current tradeline status |
| **Attachment References** |
| `proof_of_payment_url` | Data | Proof of Payment URL | No | File URL or path |
| `proof_of_au_url` | Data | Proof of AU URL | No | File URL or path |
| **Processing Status** |
| `import_status` | Select | Status | No | Pending, Success, Failed |
| `error_message` | Text | Error Message | No | Error details if failed |
| `created_customer_id` | Data | Customer ID | No | Read-only, created customer |
| `created_cart_id` | Data | Cart ID | No | Read-only, created cart |
| `created_payment_id` | Data | Payment Request ID | No | Read-only, created payment |
| `created_tradeline_id` | Data | Client Tradeline ID | No | Read-only, created client tradeline |

---

## 🏷️ is_external Flag Implementation

### Purpose
The `is_external` flag identifies records created through bulk import, allowing the system to suppress email notifications while preserving all other business logic.

### Affected DocTypes

#### 1. Customer (ERPNext Standard - Custom Field)
```json
{
  "fieldname": "is_external",
  "fieldtype": "Check",
  "label": "Is External Import",
  "default": 0,
  "description": "Marks customer created via bulk import",
  "insert_after": "disabled"
}
```

#### 2. Tradeline Cart (Custom DocType - Add Field)
```json
{
  "fieldname": "is_external",
  "fieldtype": "Check",
  "label": "Is External Import",
  "default": 0,
  "description": "Marks cart created via bulk import",
  "insert_after": "notes"
}
```

#### 3. Payment Request (Custom DocType - Add Field)
```json
{
  "fieldname": "is_external",
  "fieldtype": "Check",
  "label": "Is External Import",
  "default": 0,
  "description": "Marks payment created via bulk import",
  "insert_after": "is_manual_payment"
}
```

#### 4. Client Tradelines (Custom DocType - Add Field)
```json
{
  "fieldname": "is_external",
  "fieldtype": "Check",
  "label": "Is External Import",
  "default": 0,
  "description": "Marks tradeline created via bulk import",
  "insert_after": "refund_link"
}
```

### Email Suppression Logic

#### Modification Points

**File: `api/payment.py`**
```python
def send_payment_notification_email(payment_request_doc):
    # Add at the beginning
    if payment_request_doc.get('is_external'):
        frappe.logger().info(f"Skipping email for external payment: {payment_request_doc.name}")
        return
    # ... existing email logic
```

**File: `doctype/payment_request/payment_request.py`**
```python
def handle_status_change(self):
    # Add check in email sending sections
    if self.is_external:
        frappe.logger().info(f"Skipping email for external payment status change: {self.name}")
        return
    # ... existing email logic
```

**File: `doctype/client_tradelines/client_tradelines.py`**
```python
def send_au_assignment_email(self):
    if self.is_external:
        frappe.logger().info(f"Skipping AU assignment email for external: {self.name}")
        return
    # ... existing email logic

def send_active_status_notification_email(self):
    if self.is_external:
        frappe.logger().info(f"Skipping active notification for external: {self.name}")
        return
    # ... existing email logic

def send_refund_request_notification_email(self):
    if self.is_external:
        frappe.logger().info(f"Skipping refund notification for external: {self.name}")
        return
    # ... existing email logic
```

---

## 🔄 Import Processing Logic

### Workflow Steps

```python
# File: tradeline_import.py

class TradelineImport(Document):
    def on_submit(self):
        """Process import when submitted"""
        self.import_status = "In Progress"
        self.process_import()
    
    def process_import(self):
        """Main import processing logic"""
        self.validation_log = ""
        self.processing_log = ""
        self.successful_imports = 0
        self.failed_imports = 0
        
        for item in self.import_items:
            try:
                # Step 1: Validate item data
                self.validate_import_item(item)
                
                # Step 2: Create/Get Customer
                customer = self.create_or_get_customer(item)
                item.created_customer_id = customer.name
                
                # Step 3: Create Tradeline Cart
                cart = self.create_cart(item, customer)
                item.created_cart_id = cart.name
                
                # Step 4: Create Payment Request
                payment = self.create_payment_request(item, cart, customer)
                item.created_payment_id = payment.name
                
                # Step 5: Create Client Tradelines
                client_tradeline = self.create_client_tradeline(item, cart, payment, customer)
                item.created_tradeline_id = client_tradeline.name
                
                # Step 6: Handle Attachments
                self.attach_files(item, payment, client_tradeline)
                
                # Mark as successful
                item.import_status = "Success"
                self.successful_imports += 1
                self.log_processing(f"✓ Successfully imported: {item.customer_email} - {item.tradeline_id}")
                
            except Exception as e:
                item.import_status = "Failed"
                item.error_message = str(e)
                self.failed_imports += 1
                self.log_error(f"✗ Failed to import: {item.customer_email} - {str(e)}")
        
        # Update final status
        if self.failed_imports == 0:
            self.import_status = "Completed"
        else:
            self.import_status = "Partially Completed"
        
        self.db_set('import_status', self.import_status)
        self.db_set('successful_imports', self.successful_imports)
        self.db_set('failed_imports', self.failed_imports)
        frappe.db.commit()
```

### Validation Rules

```python
def validate_import_item(self, item):
    """Validate import item data"""
    errors = []
    
    # 1. Required fields
    if not item.customer_email:
        errors.append("Customer email is required")
    if not item.customer_name:
        errors.append("Customer name is required")
    if not item.tradeline_id:
        errors.append("Tradeline ID is required")
    if not item.quantity or item.quantity <= 0:
        errors.append("Quantity must be greater than 0")
    if not item.unit_price or item.unit_price <= 0:
        errors.append("Unit price must be greater than 0")
    
    # 2. Date chronology
    if item.cart_created_date and item.payment_approved_date:
        if item.cart_created_date > item.payment_approved_date:
            errors.append("Cart created date cannot be after payment approved date")
    
    if item.payment_approved_date and item.au_added_date:
        if item.payment_approved_date > item.au_added_date:
            errors.append("Payment approved date cannot be after AU added date")
    
    # 3. Tradeline exists and is active
    tradeline = frappe.get_doc("Tradeline", item.tradeline_id)
    if not tradeline:
        errors.append(f"Tradeline {item.tradeline_id} not found")
    
    # 4. Discount validation
    if item.discount_type:
        if not item.discount_value:
            errors.append("Discount value required when discount type is set")
        if item.discount_type == "Percentage" and (item.discount_value < 0 or item.discount_value > 100):
            errors.append("Percentage discount must be between 0 and 100")
        if item.discount_type == "Amount":
            subtotal = item.quantity * item.unit_price
            if item.discount_value < 0 or item.discount_value > subtotal:
                errors.append("Amount discount must be between 0 and subtotal")
    
    # 5. Status validation
    valid_payment_statuses = ["Pending", "Completed", "Approved", "Verified"]
    if item.payment_status not in valid_payment_statuses:
        errors.append(f"Invalid payment status: {item.payment_status}")
    
    valid_approval_statuses = ["Pending Approval", "Approved", "Rejected"]
    if item.approval_status not in valid_approval_statuses:
        errors.append(f"Invalid approval status: {item.approval_status}")
    
    valid_client_statuses = ["Pending AU", "Active", "Inactive", "Completed", "Expired"]
    if item.client_tradeline_status not in valid_client_statuses:
        errors.append(f"Invalid client tradeline status: {item.client_tradeline_status}")
    
    if errors:
        raise frappe.ValidationError("\n".join(errors))
```

### Customer Creation Logic

```python
def create_or_get_customer(self, item):
    """Create customer or get existing"""
    # Check if customer exists by email
    existing_customer = frappe.db.exists("Customer", {"email_id": item.customer_email})
    
    if existing_customer:
        customer = frappe.get_doc("Customer", existing_customer)
        self.log_processing(f"Using existing customer: {customer.name}")
        return customer
    
    # Check if User exists
    user_exists = frappe.db.exists("User", item.customer_email)
    
    if not user_exists:
        # Create User first
        user = frappe.get_doc({
            "doctype": "User",
            "email": item.customer_email,
            "first_name": item.customer_name.split()[0],
            "last_name": " ".join(item.customer_name.split()[1:]) if len(item.customer_name.split()) > 1 else "",
            "enabled": 1,
            "send_welcome_email": 0,
            "user_type": "Website User"
        })
        user.insert(ignore_permissions=True)
        self.log_processing(f"Created user: {user.name}")
    
    # Create Customer
    customer = frappe.get_doc({
        "doctype": "Customer",
        "customer_name": item.customer_name,
        "customer_type": "Individual",
        "customer_group": "Individual",
        "territory": "All Territories",
        "email_id": item.customer_email,
        "mobile_no": item.customer_phone or "",
        "is_external": 1  # Mark as external import
    })
    customer.insert(ignore_permissions=True)
    self.log_processing(f"Created customer: {customer.name}")
    
    return customer
```

### Cart Creation Logic

```python
def create_cart(self, item, customer):
    """Create Tradeline Cart"""
    cart = frappe.get_doc({
        "doctype": "Tradeline Cart",
        "user_id": item.customer_email,
        "customer": customer.name,
        "status": "Checked Out",  # Already checked out
        "payment_status": "Completed" if item.payment_status == "Completed" else "Pending",
        "is_external": 1,  # Mark as external
        "created_at": item.cart_created_date,
        "items": [{
            "tradeline": item.tradeline_id,
            "quantity": item.quantity,
            "rate": item.unit_price,
            "amount": item.quantity * item.unit_price
        }]
    })
    
    # Calculate totals with discount
    subtotal = item.quantity * item.unit_price
    discount_amount = 0
    
    if item.discount_type == "Percentage":
        discount_amount = (subtotal * item.discount_value) / 100
    elif item.discount_type == "Amount":
        discount_amount = item.discount_value
    
    cart.subtotal = subtotal
    cart.discount_amount = discount_amount
    cart.total_amount = subtotal - discount_amount
    
    cart.insert(ignore_permissions=True)
    
    # Update creation timestamp
    frappe.db.set_value("Tradeline Cart", cart.name, "creation", item.cart_created_date, update_modified=False)
    
    self.log_processing(f"Created cart: {cart.name}")
    return cart
```

### Payment Request Creation Logic

```python
def create_payment_request(self, item, cart, customer):
    """Create Payment Request"""
    payment = frappe.get_doc({
        "doctype": "Payment Request",
        "title": f"PAY-{cart.name}-IMPORT",
        "payment_method": "Bank Transfer",  # Default, can be made configurable
        "cart_id": cart.name,
        "customer": customer.name,
        "customer_name": customer.customer_name,
        "customer_email": item.customer_email,
        "amount": cart.subtotal,
        "fees": 0,  # Assuming no fees for imported data
        "total_amount": cart.total_amount,
        "status": item.payment_status,
        "approval_status": item.approval_status,
        "is_manual_payment": 1,
        "is_external": 1,  # Mark as external
        "created_at": item.cart_created_date,
        "completed_at": item.payment_approved_date if item.payment_approved_date else None
    })
    
    payment.insert(ignore_permissions=True)
    
    # Update timestamps
    frappe.db.set_value("Payment Request", payment.name, {
        "creation": item.cart_created_date,
        "modified": item.payment_approved_date if item.payment_approved_date else item.cart_created_date
    }, update_modified=False)
    
    self.log_processing(f"Created payment request: {payment.name}")
    return payment
```

### Client Tradeline Creation Logic

```python
def create_client_tradeline(self, item, cart, payment, customer):
    """Create Client Tradelines"""
    client_tradeline = frappe.get_doc({
        "doctype": "Client Tradelines",
        "customer": customer.name,
        "customer_name": customer.customer_name,
        "cart": cart.name,
        "payment_request": payment.name,
        "tradeline": item.tradeline_id,
        "tradeline_name": frappe.get_value("Tradeline", item.tradeline_id, "bank"),
        "quantity": item.quantity,
        "unit_price": item.unit_price,
        "status": item.client_tradeline_status,
        "expiry_date": item.expiry_date,
        "is_external": 1,  # Mark as external
        "created_date": item.payment_approved_date if item.payment_approved_date else item.cart_created_date,
        "completion_date": item.au_added_date if item.au_added_date else None
    })
    
    # Add discount fields
    if item.discount_type:
        client_tradeline.discount_type = item.discount_type
        client_tradeline.discount_value = item.discount_value
    
    client_tradeline.insert(ignore_permissions=True)
    
    # Update timestamps
    frappe.db.set_value("Client Tradelines", client_tradeline.name, {
        "creation": item.payment_approved_date if item.payment_approved_date else item.cart_created_date,
        "modified": item.au_added_date if item.au_added_date else item.payment_approved_date
    }, update_modified=False)
    
    self.log_processing(f"Created client tradeline: {client_tradeline.name}")
    return client_tradeline
```

---

## 📎 Attachment Handling

### File Upload Process

```python
def attach_files(self, item, payment, client_tradeline):
    """Attach proof of payment and AU files"""
    
    # 1. Proof of Payment
    if item.proof_of_payment_url:
        try:
            file_doc = self.create_file_attachment(
                file_url=item.proof_of_payment_url,
                attached_to_doctype="Payment Request",
                attached_to_name=payment.name,
                attached_to_field="proof_of_payment",
                is_private=1
            )
            payment.proof_of_payment = file_doc.file_url
            payment.save(ignore_permissions=True)
            self.log_processing(f"Attached proof of payment: {file_doc.name}")
        except Exception as e:
            self.log_error(f"Failed to attach proof of payment: {str(e)}")
    
    # 2. Proof of AU Assignment
    if item.proof_of_au_url:
        try:
            file_doc = self.create_file_attachment(
                file_url=item.proof_of_au_url,
                attached_to_doctype="Client Tradelines",
                attached_to_name=client_tradeline.name,
                attached_to_field="proof_of_au_assignment",
                is_private=1
            )
            client_tradeline.proof_of_au_assignment = file_doc.file_url
            client_tradeline.save(ignore_permissions=True)
            self.log_processing(f"Attached proof of AU: {file_doc.name}")
        except Exception as e:
            self.log_error(f"Failed to attach proof of AU: {str(e)}")

def create_file_attachment(self, file_url, attached_to_doctype, attached_to_name, attached_to_field, is_private=1):
    """Create File doctype record for attachment"""
    import requests
    from frappe.utils.file_manager import save_file
    
    # If URL is provided, download the file
    if file_url.startswith("http"):
        response = requests.get(file_url)
        file_content = response.content
        file_name = file_url.split("/")[-1]
    else:
        # Assume it's a local file path
        with open(file_url, "rb") as f:
            file_content = f.read()
        file_name = os.path.basename(file_url)
    
    # Save file
    file_doc = save_file(
        fname=file_name,
        content=file_content,
        dt=attached_to_doctype,
        dn=attached_to_name,
        folder="Home/Attachments",
        is_private=is_private
    )
    
    return file_doc
```

---

## 📝 Manual Entry Process

### How to Add Import Items

1. **Create New Tradeline Import**
   - Navigate to Tradeline Import list
   - Click "New"
   - Enter Import Title and Notes

2. **Add Import Items**
   - In the Import Items table, click "+ Add Row"
   - Fill in all required fields:
     - Customer Email
     - Customer Name
     - Tradeline (select from dropdown)
     - Quantity
     - Unit Price
     - Cart Created Date
     - Payment Approved Date
     - Payment Status
     - Approval Status
     - Client Tradeline Status
   
3. **Optional Fields**
   - Customer Phone
   - Discount Type & Value
   - AU Added Date
   - Expiry Date
   - Proof of Payment URL
   - Proof of AU URL

4. **Save as Draft**
   - Click "Save" to save without processing
   - You can add/edit/remove items while in Draft status
   - Validation happens when you submit

5. **Submit to Process**
   - Click "Submit" to trigger import processing
   - System will validate all items
   - Records will be created automatically
   - Review Processing Log for results

### Field Validation

All fields are validated before processing:
- **Email Format**: Must be valid email address
- **Dates**: Must be in chronological order
- **Tradeline**: Must exist and be active
- **Discounts**: Percentage (0-100) or Amount (≤ subtotal)
- **Statuses**: Must be from allowed values

---

## 🔒 Permissions & Security

### Role Permissions
- **System Manager**: Full access (create, read, write, delete)
- **Administrator**: Full access (create, read, write, delete)
- **All other roles**: No access

### Data Integrity
1. All imported records marked with `is_external = 1`
2. Timestamps preserved from original data
3. Validation prevents invalid date sequences
4. Customer creation respects existing records
5. Tradeline slot availability is updated

### Audit Trail
- All imports logged in Processing Log
- Failed imports recorded with error messages
- Validation log shows all validation issues
- Track changes enabled on Tradeline Import DocType

---

## ⚠️ Important Considerations

### 1. Email Suppression
- **Critical**: All email notifications are suppressed for external imports
- Modify ALL email sending functions to check `is_external` flag
- Log email suppression for audit purposes

### 2. Data Validation
- Validate tradeline availability before import
- Ensure dates are in chronological order
- Check discount calculations
- Verify status combinations are valid

### 3. Performance
- Process imports in batches if large volumes
- Use `frappe.db.commit()` after each successful record
- Log progress for monitoring

### 4. Error Handling
- Continue processing even if one record fails
- Store error messages for each failed record
- Provide summary of successful vs. failed imports

### 5. Spot Calculation
- Import triggers tradeline spot recalculation
- Ensure imported quantities don't exceed max_spots
- Validate slot availability for each tradeline

---

## 📋 Implementation Checklist

### Phase 1: DocType Creation
- [ ] Create Tradeline Import DocType with all fields
- [ ] Create Tradeline Import Item child table
- [ ] Set up permissions (System Manager, Administrator only)
- [ ] Add track_changes configuration
- [ ] Make DocType submittable (is_submittable = 1)

### Phase 2: is_external Flag
- [ ] Add is_external field to Customer (Custom Field)
- [ ] Add is_external field to Tradeline Cart
- [ ] Add is_external field to Payment Request
- [ ] Add is_external field to Client Tradelines

### Phase 3: Email Suppression
- [ ] Modify `send_payment_notification_email()` in payment.py
- [ ] Modify `handle_status_change()` in payment_request.py
- [ ] Modify `send_au_assignment_email()` in client_tradelines.py
- [ ] Modify `send_active_status_notification_email()` in client_tradelines.py
- [ ] Modify `send_refund_request_notification_email()` in client_tradelines.py
- [ ] Modify `send_removal_confirmation_email()` in client_tradelines.py
- [ ] Add logging for suppressed emails

### Phase 4: Import Logic
- [ ] Implement `process_import()` method
- [ ] Implement `validate_import_item()` method
- [ ] Implement `create_or_get_customer()` method
- [ ] Implement `create_cart()` method
- [ ] Implement `create_payment_request()` method
- [ ] Implement `create_client_tradeline()` method
- [ ] Implement `attach_files()` method
- [ ] Implement logging methods

### Phase 5: Form Enhancements
- [ ] Add field descriptions and help text
- [ ] Set up field dependencies and validations
- [ ] Configure default values
- [ ] Add custom field behaviors (auto-fetch, etc.)

### Phase 6: Testing
- [ ] Test single record import
- [ ] Test bulk import (10+ records)
- [ ] Test validation error handling
- [ ] Test customer creation (new & existing)
- [ ] Test discount calculations
- [ ] Test attachment handling
- [ ] Test email suppression
- [ ] Test spot recalculation

### Phase 7: Documentation
- [ ] Update API documentation
- [ ] Create user guide for import process
- [ ] Document Excel template format
- [ ] Add troubleshooting guide

---

## 🚀 Next Steps

1. **Review this document** with stakeholders
2. **Create Tradeline Import DocType** using Frappe Form Builder
3. **Add is_external fields** to all affected DocTypes
4. **Modify email functions** to check is_external flag
5. **Implement import processing logic** in tradeline_import.py
6. **Add form validations** and help text for user guidance
7. **Test thoroughly** with sample data entry
8. **Deploy to staging** for user acceptance testing
9. **Document** and train administrators on manual entry process

---

## 📞 Support & Questions

For questions about this design or implementation:
- **Technical Lead**: Review code in `apps/rockettradeline/rockettradeline/doctype/tradeline_import/`
- **Documentation**: This file (TRADELINE_IMPORT_README.md)
- **Related Docs**: TRADELINE_PURCHASE_FLOW.md, TRADELINE_QUICK_REFERENCE.md

---

*Document Version: 1.0*  
*Last Updated: October 12, 2025*  
*Author: AI Assistant*

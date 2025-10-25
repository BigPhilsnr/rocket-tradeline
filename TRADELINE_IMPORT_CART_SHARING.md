# Tradeline Import - Cart and Payment Request Sharing

## Overview
The Tradeline Import system now intelligently groups import items by customer email to create a single cart and payment request for all tradelines belonging to the same customer.

## Key Changes

### Before
- Each import item created its own separate cart and payment request
- Multiple items for the same customer resulted in multiple carts
- This didn't match real-world purchase behavior

### After
- Import items are grouped by `customer_email`
- All items for the same customer share:
  - ✅ **ONE User** (created or retrieved)
  - ✅ **ONE Customer** record
  - ✅ **ONE Tradeline Cart** (containing all items)
  - ✅ **ONE Payment Request** (for the total amount)
  - ✅ **Multiple Client Tradelines** (one per import item)

## Processing Flow

```
Import Submission
    ↓
Group items by customer_email
    ↓
For each customer group:
    ├─ Step 1: Create/Get User
    ├─ Step 2: Create Customer (is_external=1)
    ├─ Step 3: Create Cart with all items (is_external=1)
    │          - Calculates total subtotal
    │          - Calculates total discount
    │          - Calculates total amount
    ├─ Step 4: Create Payment Request (is_external=1)
    │          - References the shared cart
    │          - Contains total amount
    └─ Step 5: Create Client Tradelines (is_external=1)
               - One per import item
               - Each references the shared cart and payment
               - Individual amounts calculated per item
```

## Example Scenario

### Import Data:
```
Row 1: john@example.com, Tradeline A, Qty 1, $100
Row 2: john@example.com, Tradeline B, Qty 2, $150
Row 3: jane@example.com, Tradeline C, Qty 1, $200
```

### Created Records:

#### For john@example.com:
- **1 User**: john@example.com
- **1 Customer**: john@example.com
- **1 Cart**: Contains 2 items (Tradeline A + Tradeline B)
  - Subtotal: $400 ($100 + $300)
  - Total: $400 (minus any discounts)
- **1 Payment Request**: $400
- **2 Client Tradelines**:
  - Client Tradeline 1: Tradeline A x 1 = $100
  - Client Tradeline 2: Tradeline B x 2 = $300

#### For jane@example.com:
- **1 User**: jane@example.com
- **1 Customer**: jane@example.com
- **1 Cart**: Contains 1 item (Tradeline C)
  - Subtotal: $200
  - Total: $200 (minus any discounts)
- **1 Payment Request**: $200
- **1 Client Tradeline**:
  - Client Tradeline 1: Tradeline C x 1 = $200

## Benefits

1. **Accurate Representation**: Matches actual purchase behavior where customers buy multiple tradelines in one transaction
2. **Simplified Tracking**: One cart and payment per customer makes reporting and tracking easier
3. **Better Analytics**: Total cart value and payment amount accurately reflect customer purchase behavior
4. **Reduced Records**: Fewer cart and payment records in the database
5. **Consistent Data**: All tradelines from the same purchase are linked to the same cart and payment

## Cart Amount Calculation

### Cart Level (Shared):
```python
total_subtotal = sum(item.quantity * item.unit_price for each item)
total_discount = sum(item_discount_amount for each item)
cart.total_amount = total_subtotal - total_discount
```

### Client Tradeline Level (Individual):
```python
item_subtotal = item.quantity * item.unit_price
item_discount_amount = calculated based on discount_type and discount_value
client_tradeline.total_amount = item_subtotal - item_discount_amount
```

## Processing Log Example

```
=== Import Processing Started at 2025-10-12 14:30:00 ===

Found 2 unique customers
Processing 3 total items

=== Processing Customer: john@example.com (2 items) ===
Step 1: Creating/Getting User for john@example.com
✓ User: john@example.com
Step 2: Creating Customer
✓ Customer: CUST-00001
Step 3: Creating Tradeline Cart with 2 items
  → Item: TL-001 x 1 = $100.00
  → Item: TL-002 x 2 = $300.00
✓ Cart: CART-0001 (subtotal=400.0, discount=0.0, total=400.0, is_external=1)
Step 4: Creating Payment Request
✓ Payment Request: PR-0001
Step 5: Creating 2 Client Tradelines
  ✓ Item 1/2: Client Tradeline CT-0001
  ✓ Item 2/2: Client Tradeline CT-0002

=== Processing Customer: jane@example.com (1 items) ===
Step 1: Creating/Getting User for jane@example.com
✓ User: jane@example.com
Step 2: Creating Customer
✓ Customer: CUST-00002
Step 3: Creating Tradeline Cart with 1 items
  → Item: TL-003 x 1 = $200.00
✓ Cart: CART-0002 (subtotal=200.0, discount=0.0, total=200.0, is_external=1)
Step 4: Creating Payment Request
✓ Payment Request: PR-0002
Step 5: Creating 1 Client Tradelines
  ✓ Item 1/1: Client Tradeline CT-0003

=== Import Processing Completed at 2025-10-12 14:30:05 ===
Total Records: 3
Successful: 3
Failed: 0
Processing Time: 5.23 seconds
```

## Implementation Details

### Key Methods:

1. **`on_submit()`**: Groups items by customer email and processes each group
2. **`process_customer_group()`**: Handles all items for a single customer
3. **`create_cart_with_items()`**: Creates a cart containing multiple tradeline items
4. **`create_client_tradeline()`**: Creates individual client tradelines with correct amounts

### Field Mapping:

#### Tradeline Import Item → Shared Cart:
- `cart_created_date` → Uses earliest date from all items
- All items → Combined into cart.items (if field exists)
- Total amounts → Sum of all item amounts

#### Tradeline Import Item → Individual Client Tradeline:
- Each item → One Client Tradeline
- Individual amounts calculated per item
- All reference the same cart and payment

## Notes

- Items are grouped by **exact email match** (case-sensitive)
- If any item in a group fails, other items in the same group still process
- All created records have `is_external=1` to suppress emails
- The cart uses the **earliest cart_created_date** from all items in the group
- Individual Client Tradelines maintain their own amounts and discounts

## Date Created
October 12, 2025

## Last Updated
October 12, 2025

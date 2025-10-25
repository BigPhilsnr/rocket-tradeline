# Tradeline Import - Bug Fixes

## Issue Summary
The Tradeline Import was failing on submission with errors related to field name mismatches and missing required fields.

## Fixes Applied (October 12, 2025)

### 1. Fixed Tradeline Name Fetch (`tradeline_import_item.json`)
**Problem**: The `fetch_from` field was trying to fetch `tradeline_id.bank.bank_name`, which doesn't exist in the database structure.

**Solution**: Changed `fetch_from` to `tradeline_id.bank` since:
- Tradeline Bank uses `autoname: field:bank_name`
- The `name` field IS the bank_name (e.g., "CITI")
- Tradeline's `bank` field stores the name directly

```json
// Before
"fetch_from": "tradeline_id.bank.bank_name"

// After
"fetch_from": "tradeline_id.bank"
```

### 2. Fixed Cart Item Field Names (`tradeline_import.py`)
**Problem**: Tradeline Cart Item uses different field names than what was being set.

**Solution**: Updated `create_cart_with_items()` method to use correct field names:
- `tradeline` (not `tradeline_id`)
- `rate` (not `unit_price`)
- `amount` (not `total_amount`)
- Removed discount fields (not supported at item level)

```python
# Correct field mapping
cart_items.append({
    "tradeline": item.tradeline_id,  # Correct field name
    "quantity": item.quantity,
    "rate": item.unit_price,  # Changed from 'unit_price'
    "amount": item_subtotal - item_discount_amount  # Changed from multiple fields
})
```

### 3. Fixed Payment Request Field Names (`tradeline_import.py`)
**Problem**: Payment Request uses different field names and requires additional fields.

**Solution**: Updated `create_payment_request()` method:
- `customer` (not `customer_id`)
- `status` (not `payment_status`)
- `approved_at` (not `approved_date`)
- Added required `title` field (auto-generated)
- Added required `payment_method` field
- Added required `total_amount` field
- Set `is_manual_payment` to 1 for imported records
- Set `completed_at` when status is "Completed"

```python
# Correct field mapping
payment = frappe.get_doc({
    "doctype": "Payment Request",
    "title": payment_title,  # Required field, auto-generated
    "cart_id": cart.name,
    "customer": cart.customer,  # Changed from 'customer_id'
    "amount": cart.total_amount,
    "total_amount": cart.total_amount,  # Required field
    "payment_method": payment_method,  # Required field
    "status": item.payment_status,  # Changed from 'payment_status'
    "approval_status": item.approval_status,
    "proof_of_payment": item.proof_of_payment_url,
    "is_external": 1 if self.suppress_emails else 0,
    "is_manual_payment": 1,  # Mark as manual payment
    "approved_at": item.payment_approved_date,  # Changed from 'approved_date'
    "completed_at": item.payment_approved_date if item.payment_status == "Completed" else None
})
```

### 4. Added Fail-Fast Behavior (`tradeline_import.py`)
**Problem**: The import would continue processing even if a group failed, leading to partial imports.

**Solution**: Added exception handling that fails the entire submission if any customer group fails:

```python
except Exception as e:
    # Mark all items in this group as failed
    for item in items:
        item.import_status = "Failed"
        item.error_message = str(e)
        self.failed_imports += 1
    
    error_msg = f"✗ {display_name} failed: {str(e)}"
    processing_logs.append(error_msg)
    frappe.log_error(
        title=f"Tradeline Import Failed - {display_name}",
        message=frappe.get_traceback()
    )
    
    # Fail the entire submission if any group fails
    self.processing_log = "\n".join(processing_logs)
    self.db_update()
    frappe.db.commit()
    frappe.throw(_(f"Import failed for {display_name}: {str(e)}"))
```

## Field Mapping Reference

### Tradeline Import Item → Tradeline Cart Item
| Import Field | Cart Item Field | Notes |
|-------------|----------------|-------|
| `tradeline_id` | `tradeline` | Link to Tradeline |
| `quantity` | `quantity` | Same field name |
| `unit_price` | `rate` | Different name |
| `total_amount` | `amount` | Different name |

### Tradeline Import Item → Payment Request
| Import Field | Payment Request Field | Notes |
|-------------|----------------------|-------|
| N/A | `title` | Auto-generated |
| N/A | `payment_method` | Fetched from Payment Configuration |
| `cart.customer` | `customer` | Not `customer_id` |
| `cart.total_amount` | `amount` | Same field name |
| `cart.total_amount` | `total_amount` | Required field |
| `payment_status` | `status` | Different name |
| `approval_status` | `approval_status` | Same field name |
| `payment_approved_date` | `approved_at` | Different name |
| `payment_approved_date` | `completed_at` | Only if status is "Completed" |

### Tradeline Import Item → Client Tradelines
| Import Field | Client Tradeline Field | Notes |
|-------------|----------------------|-------|
| All fields match directly | Same field names | No mapping issues |

## Testing Checklist

Before considering this complete, test the following:

- [ ] Create Tradeline Import with existing customer (manual selection)
- [ ] Create Tradeline Import with new customer (auto-creation)
- [ ] Verify Cart creation with correct item fields
- [ ] Verify Payment Request creation with all required fields
- [ ] Verify Client Tradelines creation
- [ ] Verify file attachments are handled correctly
- [ ] Verify is_external flag is set correctly
- [ ] Verify submission fails if any step fails
- [ ] Check processing logs for detailed information
- [ ] Verify email suppression (if suppress_emails is checked)

## Migration Commands

To apply these fixes to your system:

```bash
cd /home/frappe/frappe-bench
bench migrate
bench --site rockettradeline.com clear-cache
bench restart
```

## Next Steps

1. **Hard refresh your browser** (Ctrl+Shift+R or Cmd+Shift+R)
2. Try creating a new Tradeline Import with the existing customer "Philip Buyer"
3. Select tradeline "00003" (CITI)
4. Fill in all required fields
5. Submit and verify the import completes successfully
6. Check the processing log for detailed information

## Related Files

- `/apps/rockettradeline/rockettradeline/rockettradeline/doctype/tradeline_import/tradeline_import.py`
- `/apps/rockettradeline/rockettradeline/rockettradeline/doctype/tradeline_import_item/tradeline_import_item.json`
- `/apps/rockettradeline/rockettradeline/rockettradeline/doctype/tradeline_cart/tradeline_cart.json`
- `/apps/rockettradeline/rockettradeline/rockettradeline/doctype/tradeline_cart_item/tradeline_cart_item.json`
- `/apps/rockettradeline/rockettradeline/rockettradeline/doctype/payment_request/payment_request.json`
- `/apps/rockettradeline/rockettradeline/rockettradeline/doctype/client_tradelines/client_tradelines.json`

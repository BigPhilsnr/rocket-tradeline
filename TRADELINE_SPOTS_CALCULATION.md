# Tradeline Remaining Spots Calculation System

## Overview
This document describes the centralized system for calculating and managing tradeline remaining spots based on Payment Request and Client Tradelines statuses.

## Core Logic

### When Spots Are Considered "Taken"
1. **Payment Request with status "Pending Approval"**
   - All tradelines in the cart linked to this payment request are considered taken
   - Spots remain taken until the payment request is approved or rejected

2. **Client Tradelines with statuses:**
   - `Active`: Spots are actively being used
   - `Pending AU`: AU is being added, spots are reserved
   - `Inactive`: Temporarily inactive but still reserved

### When Spots Are Released
1. **Payment Request with status "Rejected"**
   - All tradelines in the cart are immediately available again
   
2. **Client Tradelines with statuses:**
   - `Expired`: Tradeline period has ended
   - `Refunded`: Payment was refunded, spots released
   - `Cancelled`: Order was cancelled

## Implementation Files

### 1. Core Utility: `/apps/rockettradeline/rockettradeline/utils/tradeline_spots.py`

#### Main Functions:

**`recalculate_tradeline_remaining_spots(tradeline_name)`**
- Recalculates remaining spots for a single tradeline
- Counts spots from:
  - Pending Approval Payment Requests (via cart items)
  - Active Client Tradelines (Active, Pending AU, Inactive statuses)
- Updates `purchased_spots` and `remaining_spots` fields in Tradeline doctype
- Returns success status and spot counts

**`recalculate_all_tradeline_spots_from_payment_request(payment_request_name)`**
- Recalculates spots for all tradelines in a payment request's cart
- Called automatically when payment request status changes

**`recalculate_spots_from_client_tradeline(client_tradeline_name)`**
- Recalculates spots for the tradeline linked to a client tradeline
- Called automatically when client tradeline status changes

**`check_tradeline_availability(tradeline_name, requested_quantity)`**
- Checks if enough spots are available for a requested quantity
- Recalculates spots first to ensure accuracy
- Returns availability status with detailed information

**`check_cart_availability(cart_id)`**
- Validates all tradelines in a cart have sufficient spots
- Returns detailed availability information for each item

**`recalculate_all_tradelines()`**
- Recalculates spots for all active tradelines
- Can be called manually or by scheduler

### 2. Payment Request Updates: `/apps/rockettradeline/rockettradeline/rockettradeline/doctype/payment_request/payment_request.py`

**Modified Methods:**
- `on_update()`: Now triggers spot recalculation when status or approval_status changes
- `recalculate_tradeline_spots_on_status_change()`: New method that calls the centralized utility

**Trigger Points:**
- Status changes: Draft → Pending Approval → Approved/Rejected
- Approval status changes: Pending Approval → Approved/Rejected

### 3. Client Tradelines Updates: `/apps/rockettradeline/rockettradeline/rockettradeline/doctype/client_tradelines/client_tradelines.py`

**Modified Methods:**
- `on_update()`: Triggers spot recalculation when status or quantity changes
- `recalculate_tradeline_remaining_spots_v2()`: New method using centralized utility

**Trigger Points:**
- Status changes: Pending AU → Active → Expired/Refunded
- Quantity changes (unless status is Refund Requested)

### 4. Cart API Updates: `/apps/rockettradeline/rockettradeline/api/cart.py`

**Modified Functions:**
- `validate_cart_slots(cart)`: Now uses centralized availability check
- `checkout_cart()`: Already validates slots before checkout

**Validation Points:**
- Before cart checkout
- Uses `check_cart_availability()` for real-time validation

### 5. Payment API Updates: `/apps/rockettradeline/rockettradeline/api/payment.py`

**Modified Functions:**
- `upload_payment_proof()`: Added availability check before creating payment request

**Validation Points:**
- Before uploading proof of payment
- Returns 409 Conflict status if spots unavailable

### 6. Scheduler Tasks Updates: `/apps/rockettradeline/rockettradeline/tasks.py`

**Modified Functions:**
- `check_and_expire_client_tradelines()`: Recalculates spots after expiring tradelines

**Trigger Points:**
- Runs hourly via scheduler
- Recalculates spots for all tradelines that had expired client tradelines

### 7. Tradeline API: `/apps/rockettradeline/rockettradeline/api/tradeline.py`

**New Endpoint:**
```python
@frappe.whitelist(allow_guest=True)
@jwt_required()
def recalculate_tradeline_spots(tradeline_id=None)
```
- Admin-only endpoint
- Manually trigger recalculation for one or all tradelines
- Useful for maintenance and troubleshooting

## Calculation Formula

```python
taken_spots = (
    spots_in_pending_approval_payment_requests +
    spots_in_active_client_tradelines +
    spots_in_pending_au_client_tradelines +
    spots_in_inactive_client_tradelines
)

remaining_spots = max(0, max_spots - taken_spots)
```

## Status Flow Examples

### Example 1: Normal Purchase Flow
1. User adds tradeline to cart (no spots taken yet)
2. User checks out → Cart status: "Checked Out"
3. User uploads payment proof → Payment Request created with "Pending Approval"
   - **Spots are NOW taken** (pending approval counts)
4. Admin approves → Payment Request: "Approved", Client Tradelines created: "Pending AU"
   - Spots remain taken (moved from payment request to client tradeline)
5. AU added → Client Tradelines: "Active"
   - Spots remain taken
6. Tradeline expires → Client Tradelines: "Expired"
   - **Spots are NOW released**

### Example 2: Rejected Payment
1. User uploads payment proof → Payment Request: "Pending Approval"
   - Spots taken
2. Admin rejects → Payment Request: "Rejected"
   - **Spots immediately released**

### Example 3: Refund Request
1. Active tradeline → Client Tradelines: "Active"
   - Spots taken
2. Client requests refund → Client Tradelines: "Refund Requested"
   - Spots remain taken (not yet refunded)
3. Admin processes refund → Client Tradelines: "Refunded"
   - **Spots released**

## API Endpoints

### Manual Recalculation (Admin Only)
```bash
# Recalculate single tradeline
POST /api/method/rockettradeline.api.tradeline.recalculate_tradeline_spots
{
  "tradeline_id": "TL-00123"
}

# Recalculate all tradelines
POST /api/method/rockettradeline.api.tradeline.recalculate_tradeline_spots
{
  "tradeline_id": null
}
```

### Check Availability (Public)
The availability is automatically checked during:
- Cart checkout
- Payment proof upload
- Any cart validation

## Database Fields Updated

### Tradeline DocType
- `purchased_spots`: Total spots currently taken
- `remaining_spots`: Available spots for purchase

## Error Handling

All recalculation functions include comprehensive error handling:
- Errors are logged to Frappe Error Log
- Functions return success/failure status
- Failed recalculations don't block the main operation
- Detailed error messages for debugging

## Performance Considerations

1. **Automatic Recalculation**: Triggered only when necessary (status changes)
2. **Batch Processing**: Scheduler recalculates multiple tradelines efficiently
3. **Database Optimization**: Uses indexed queries for counting spots
4. **Caching**: Relies on database state, no additional caching needed

## Testing Checklist

- [ ] Create cart with tradeline → Check spots not taken
- [ ] Upload payment proof → Check spots taken (pending approval)
- [ ] Approve payment → Check spots remain taken (client tradeline created)
- [ ] Reject payment → Check spots released
- [ ] Expire client tradeline → Check spots released
- [ ] Request refund → Check spots remain taken until refunded
- [ ] Process refund → Check spots released
- [ ] Manual recalculation API → Check all tradelines updated correctly
- [ ] Cart checkout with insufficient spots → Check validation blocks checkout
- [ ] Payment proof upload with insufficient spots → Check validation blocks upload

## Maintenance

### Scheduled Jobs
The following cron job includes spot recalculation:
- `check_and_expire_client_tradelines`: Hourly, recalculates after expiring tradelines

### Manual Recalculation
If spot counts become out of sync, administrators can trigger manual recalculation:
1. Via API endpoint (recommended)
2. Via bench console: `frappe.call('rockettradeline.utils.tradeline_spots.recalculate_all_tradelines')`

## Future Enhancements

Potential improvements:
1. Dashboard showing real-time availability metrics
2. Alert system for low availability tradelines
3. Automatic rebalancing suggestions
4. Historical spot usage analytics
5. Predictive availability forecasting

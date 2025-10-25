# 🚀 Rockettradeline API Documentation

A comprehensive tradeline management system built on Frappe Framework with powerful cart management, payment processing, and user authentication features.

## 📋 Table of Contents

- [Overview](#overview)
- [Base URL](#base-url)
- [Authentication](#authentication)
- [API Endpoints](#api-endpoints)
  - [Authentication APIs](#authentication-apis)
  - [Tradeline APIs](#tradeline-apis)
  - [Cart Management APIs](#cart-management-apis)
  - [Payment APIs](#payment-apis)
  - [User Management APIs](#user-management-apis)
- [Response Format](#response-format)
- [Error Codes](#error-codes)
- [Rate Limiting](#rate-limiting)
- [SDKs & Examples](#sdks--examples)

## 🎯 Overview

The Rockettradeline API provides a complete solution for managing tradelines, shopping carts, payments, and user authentication. It's built on Frappe Framework and offers both RESTful APIs and advanced features like JWT authentication, real-time cart management, and secure payment processing.

### Key Features
- 🔐 **JWT Authentication** - Secure token-based authentication
- 🛒 **Advanced Cart Management** - Full shopping cart lifecycle
- 💳 **Payment Processing** - Multiple payment methods and fee calculations
- 📧 **Email Verification** - Automated email verification system
- 👥 **User Management** - Complete user lifecycle management
- 🏦 **Tradeline Management** - Comprehensive tradeline operations

## 🌐 Base URL

```
Production: https://rockettradeline.com/api/method/
Staging: https://www.rockettradeline.com/api/method/
```

## 🔐 Authentication

The API uses JWT (JSON Web Token) authentication. Include the token in the request headers:

```http
X-Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Authentication Flow

1. **Sign Up** → Create account with email verification
2. **Login** → Get JWT token
3. **Use Token** → Include in all authenticated requests
4. **Refresh Token** → Extend token expiry

---

## 📚 API Endpoints

### 🔑 Authentication APIs

#### POST `/rockettradeline.api.auth.sign_up`
Create a new user account with email verification.

**Request Body:**
```json
{
  "email": "user@example.com",
  "full_name": "John Doe",
  "password": "securepassword123",
  "phone": "+1234567890"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Account created successfully! Please check your email to verify your account before logging in.",
  "email_sent": true,
  "user": {
    "name": "user@example.com",
    "email": "user@example.com",
    "full_name": "John Doe",
    "phone": "+1234567890",
    "email_verified": false
  },
  "customer": {
    "name": "CUST-00001",
    "customer_name": "John Doe",
    "customer_type": "Individual",
    "email_id": "user@example.com",
    "mobile_no": "+1234567890"
  }
}
```

#### POST `/rockettradeline.api.auth.login`
Authenticate user and receive JWT token.

**Request Body:**
```json
{
  "usr": "user@example.com",
  "pwd": "securepassword123"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Login successful",
  "authorization_token": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 86400,
  "user": {
    "name": "user@example.com",
    "email": "user@example.com",
    "full_name": "John Doe",
    "user_image": null,
    "phone": "+1234567890",
    "role_profile_name": null,
    "roles": ["Customer"]
  },
  "customer": {
    "name": "CUST-00001",
    "customer_name": "John Doe",
    "customer_type": "Individual",
    "email_id": "user@example.com",
    "mobile_no": "+1234567890"
  }
}
```

#### GET `/rockettradeline.api.auth.get_current_user`
Get current authenticated user details.

**Headers:** `X-Authorization: Bearer {token}`

**Response:**
```json
{
  "success": true,
  "user": {
    "name": "user@example.com",
    "email": "user@example.com",
    "full_name": "John Doe",
    "user_image": null,
    "phone": "+1234567890",
    "roles": ["Customer"],
    "user_type": "Website User",
    "enabled": true
  },
  "customer": {
    "name": "CUST-00001",
    "customer_name": "John Doe",
    "customer_type": "Individual",
    "email_id": "user@example.com",
    "mobile_no": "+1234567890",
    "addresses": []
  }
}
```

#### PUT `/rockettradeline.api.auth.update_profile`
Update user profile information.

**Headers:** `X-Authorization: Bearer {token}`

**Request Body:**
```json
{
  "full_name": "John Smith",
  "phone": "+1234567890",
  "gender": "Male",
  "date_of_birth": "1990-01-01",
  "social_security_number": "123-45-6789",
  "address_line1": "123 Main St",
  "address_line2": "Apt 4B",
  "city": "New York",
  "state": "NY",
  "zipcode": "10001",
  "country": "United States",
  "address_type": "Personal"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Profile updated successfully",
  "user": {
    "name": "user@example.com",
    "email": "user@example.com",
    "full_name": "John Smith",
    "phone": "+1234567890",
    "user_image": null,
    "birth_date": "1990-01-01"
  },
  "customer": {
    "name": "CUST-00001",
    "customer_name": "John Smith",
    "customer_type": "Individual",
    "email_id": "user@example.com",
    "mobile_no": "+1234567890",
    "gender": "Male",
    "tax_id": "123-45-6789"
  },
  "address": {
    "name": "ADDR-00001",
    "address_title": "John Smith - Personal",
    "address_type": "Personal",
    "address_line1": "123 Main St",
    "address_line2": "Apt 4B",
    "city": "New York",
    "state": "NY",
    "pincode": "10001",
    "country": "United States"
  }
}
```

#### GET `/rockettradeline.api.auth.verify_email?token={verification_token}`
Verify user email address.

**Response:** HTML page with verification status

#### POST `/rockettradeline.api.auth.resend_verification_email`
Resend email verification.

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

#### POST `/rockettradeline.api.auth.refresh_token`
Refresh JWT token.

**Headers:** `X-Authorization: Bearer {token}`

**Response:**
```json
{
  "success": true,
  "message": "Token refreshed successfully",
  "authorization_token": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 86400
}
```

---

### 🏦 Tradeline APIs

#### GET `/rockettradeline.api.tradeline.get_tradelines`
Get list of available tradelines with filtering and pagination.

**Parameters:**
- `limit` (int): Number of records to return (default: 20)
- `start` (int): Starting offset (default: 0)
- `search` (string): Search by bank name
- `filters` (JSON): Advanced filtering options

**Example Request:**
```http
GET /api/method/rockettradeline.api.tradeline.get_tradelines?limit=10&start=0&search=Chase&filters={"min_price":100,"max_price":500}
```

**Response:**
```json
{
  "success": true,
  "tradelines": [
    {
      "name": "00017",
      "bank": "JPMCB Chase",
      "age_year": 2023,
      "age_month": 0,
      "credit_limit": 22400,
      "price": 285.0,
      "max_spots": 4,
      "remaining_spots": 3,
      "closing_date": 14,
      "credit_utilization_rate": 0.0,
      "status": "Active",
      "bank_name": "JPMCB Chase"
    }
  ]
}
```

#### GET `/rockettradeline.api.tradeline.get_tradeline`
Get detailed information about a specific tradeline.

**Parameters:**
- `tradeline_id` (string): Tradeline ID

**Response:**
```json
{
  "success": true,
  "tradeline": {
    "name": "00017",
    "bank": "JPMCB Chase",
    "bank_name": "JPMCB Chase",
    "age_year": 2023,
    "age_month": 0,
    "credit_limit": 22400,
    "price": 285.0,
    "max_spots": 4,
    "remaining_spots": 3,
    "purchased_spots": 1,
    "closing_date": 14,
    "credit_utilization_rate": 0.0,
    "status": "Active",
    "balance": 0,
    "card_holder": {
      "name": "CH-00001",
      "fullname": "John Cardholder",
      "email": "cardholder@example.com",
      "phone": "+1234567890"
    },
    "mailing_address": {
      "name": "MA-00001"
    }
  }
}
```

#### GET `/rockettradeline.api.tradeline.get_banks`
Get list of available banks.

**Response:**
```json
{
  "success": true,
  "banks": [
    {
      "name": "BANK-00001",
      "bank_name": "Chase",
      "image": "/files/chase-logo.png"
    },
    {
      "name": "BANK-00002",
      "bank_name": "Bank of America",
      "image": "/files/boa-logo.png"
    }
  ]
}
```

#### POST `/rockettradeline.api.tradeline.create_tradeline` 🔒
Create a new tradeline (requires authentication and permissions).

**Headers:** `X-Authorization: Bearer {token}`

**Request Body:**
```json
{
  "bank": "BANK-00001",
  "age_year": 2020,
  "age_month": 6,
  "credit_limit": 15000,
  "price": 250.0,
  "max_spots": 5,
  "closing_date": 15,
  "card_holder": "CH-00001",
  "mailing_address": "MA-00001",
  "credit_utilization_rate": 0.0,
  "balance": 0,
  "status": "Active"
}
```

---

### 🛒 Cart Management APIs

#### POST `/rockettradeline.api.cart.create_cart` 🔒
Create a new shopping cart.

**Headers:** `X-Authorization: Bearer {token}`

**Response:**
```json
{
  "success": true,
  "message": "Cart created successfully",
  "cart": {
    "name": "CART-0018",
    "user_id": "user@example.com",
    "customer": "CUST-00001",
    "status": "Active",
    "cart_expiry": "2025-09-16 01:48:04.844866",
    "payment_mode": null,
    "payment_status": "Pending",
    "subtotal": 0.0,
    "discount_amount": 0.0,
    "tax_amount": 0.0,
    "total_amount": 0.0,
    "items": []
  },
  "cart_id": "CART-0018"
}
```

#### GET `/rockettradeline.api.cart.get_cart` 🔒
Get current active cart or specific cart by ID.

**Headers:** `X-Authorization: Bearer {token}`

**Parameters:**
- `cart_id` (optional): Specific cart ID

**Response:**
```json
{
  "success": true,
  "cart": {
    "name": "CART-0018",
    "user_id": "user@example.com",
    "customer": "CUST-00001",
    "status": "Active",
    "subtotal": 600.0,
    "discount_amount": 0.0,
    "tax_amount": 0.0,
    "total_amount": 600.0,
    "items": [
      {
        "name": "tkesje5e45",
        "tradeline": "00018",
        "tradeline_name": "BANK OF AMERICA",
        "quantity": 2,
        "rate": 300.0,
        "amount": 600.0,
        "tradeline_details": {
          "bank": "BANK OF AMERICA",
          "age_year": 2016,
          "age_month": 0,
          "credit_limit": 10300,
          "max_spots": 2,
          "status": "Active"
        }
      }
    ]
  },
  "cart_summary": {
    "cart_id": "CART-0018",
    "item_count": 1,
    "subtotal": 600.0,
    "discount_amount": 0.0,
    "tax_amount": 0.0,
    "total_amount": 600.0,
    "is_expired": false
  }
}
```

#### POST `/rockettradeline.api.cart.add_to_cart` 🔒
Add tradeline to cart.

**Headers:** `X-Authorization: Bearer {token}`

**Request Body:**
```json
{
  "tradeline_id": "00018",
  "quantity": 1,
  "cart_id": "CART-0018"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Item added to cart successfully",
  "cart": {
    "name": "CART-0018",
    "total_amount": 300.0,
    "items": [
      {
        "tradeline": "00018",
        "tradeline_name": "BANK OF AMERICA",
        "quantity": 1,
        "rate": 300.0,
        "amount": 300.0
      }
    ]
  },
  "cart_summary": {
    "cart_id": "CART-0018",
    "item_count": 1,
    "total_amount": 300.0
  }
}
```

#### PUT `/rockettradeline.api.cart.update_cart_item` 🔒
Update item quantity in cart.

**Headers:** `X-Authorization: Bearer {token}`

**Request Body:**
```json
{
  "tradeline_id": "00018",
  "quantity": 2,
  "cart_id": "CART-0018"
}
```

#### DELETE `/rockettradeline.api.cart.remove_from_cart` 🔒
Remove item from cart.

**Headers:** `X-Authorization: Bearer {token}`

**Request Body:**
```json
{
  "tradeline_id": "00018",
  "cart_id": "CART-0018"
}
```

#### DELETE `/rockettradeline.api.cart.clear_cart` 🔒
Clear all items from cart.

**Headers:** `X-Authorization: Bearer {token}`

**Request Body:**
```json
{
  "cart_id": "CART-0018"
}
```

#### POST `/rockettradeline.api.cart.apply_discount` 🔒
Apply discount to cart.

**Headers:** `X-Authorization: Bearer {token}`

**Request Body:**
```json
{
  "discount_type": "percentage",
  "discount_value": 10,
  "cart_id": "CART-0018"
}
```

#### PUT `/rockettradeline.api.cart.update_payment_mode` 🔒
Update cart payment mode.

**Headers:** `X-Authorization: Bearer {token}`

**Request Body:**
```json
{
  "payment_mode": "Credit Card",
  "cart_id": "CART-0018"
}
```

#### POST `/rockettradeline.api.cart.checkout_cart` 🔒
Checkout cart and create order.

**Headers:** `X-Authorization: Bearer {token}`

**Request Body:**
```json
{
  "cart_id": "CART-0018"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Checkout completed successfully",
  "cart": {
    "name": "CART-0018",
    "status": "Checked Out",
    "total_amount": 600.0
  },
  "sales_order": "SO-00001",
  "next_steps": "Please proceed with payment processing"
}
```

#### GET `/rockettradeline.api.cart.get_cart_history` 🔒
Get user's cart history with pagination.

**Headers:** `X-Authorization: Bearer {token}`

**Parameters:**
- `limit` (int): Number of records (default: 20)
- `start` (int): Starting offset (default: 0)

**Response:**
```json
{
  "success": true,
  "carts": [
    {
      "name": "CART-0018",
      "status": "Checked Out",
      "total_amount": 600.0,
      "payment_mode": "Credit Card",
      "payment_status": "Pending",
      "creation": "2025-08-17 01:48:04.862608",
      "modified": "2025-08-17 01:49:19.023417"
    }
  ],
  "pagination": {
    "total": 1,
    "limit": 20,
    "start": 0,
    "has_next": false
  }
}
```

#### PUT `/rockettradeline.api.cart.extend_cart_expiry` 🔒
Extend cart expiry date.

**Headers:** `X-Authorization: Bearer {token}`

**Request Body:**
```json
{
  "days": 15,
  "cart_id": "CART-0018"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Cart expiry extended by 15 days",
  "new_expiry": "2025-10-01 01:48:04.844866"
}
```

---

### 💳 Payment APIs

#### GET `/rockettradeline.api.cart.get_payment_methods` 🔒
Get available payment methods.

**Headers:** `X-Authorization: Bearer {token}`

**Response:**
```json
{
  "success": true,
  "payment_methods": [
    {
      "name": "PAY-CONF-0001",
      "payment_method": "credit_card",
      "payment_type": "Card",
      "min_amount": 1.0,
      "max_amount": 10000.0,
      "fixed_fee": 0.3,
      "percentage_fee": 2.9,
      "instructions": "Enter your credit card details to complete the payment",
      "icon": "credit-card",
      "display_name": "Credit Card"
    },
    {
      "name": "PAY-CONF-0002",
      "payment_method": "paypal",
      "payment_type": "Digital Wallet",
      "min_amount": 1.0,
      "max_amount": 10000.0,
      "fixed_fee": 0.3,
      "percentage_fee": 2.9,
      "instructions": "You will be redirected to PayPal to complete your payment",
      "icon": "paypal",
      "display_name": "PayPal"
    }
  ]
}
```

#### POST `/rockettradeline.api.cart.calculate_payment_fees` 🔒
Calculate payment fees for amount and method.

**Headers:** `X-Authorization: Bearer {token}`

**Request Body:**
```json
{
  "amount": 600.0,
  "payment_method": "credit_card"
}
```

**Response:**
```json
{
  "success": true,
  "amount": 600.0,
  "fees": {
    "fixed_fee": 0.3,
    "percentage_fee": 17.4,
    "total_fee": 17.7
  },
  "total_amount": 617.7,
  "payment_method": "credit_card"
}
```

#### POST `/rockettradeline.api.cart.create_payment_request` 🔒
Create payment request for cart.

**Headers:** `X-Authorization: Bearer {token}`

**Request Body:**
```json
{
  "payment_method": "credit_card",
  "cart_id": "CART-0018",
  "customer_email": "user@example.com"
}
```

#### GET `/rockettradeline.api.cart.get_cart_payment_status` 🔒
Get payment status for cart.

**Headers:** `X-Authorization: Bearer {token}`

**Parameters:**
- `cart_id` (optional): Specific cart ID

**Response:**
```json
{
  "success": true,
  "cart_status": "Active",
  "payment_requests": [
    {
      "name": "PR-00001",
      "status": "Pending",
      "payment_method": "credit_card",
      "total_amount": 617.7,
      "transaction_id": "txn_12345",
      "created_at": "2025-08-17 01:49:00",
      "completed_at": null
    }
  ],
  "has_pending_payment": true
}
```

---

### � Client Tradeline Discount APIs

#### POST `/rockettradeline.api.client_tradelines.apply_discount` 🔒
Apply a discount to an existing Client Tradeline.

**Headers:** `X-Authorization: Bearer {token}`

**Request Body:**
```json
{
  "client_tradeline_id": "CTL-00001",
  "discount_type": "Percentage",
  "discount_value": 10
}
```

**Response:**
```json
{
  "success": true,
  "message": "Discount applied successfully",
  "client_tradeline": {
    "name": "CTL-00001",
    "customer": "CUST-00001",
    "customer_name": "John Doe",
    "tradeline": "TL-0001",
    "tradeline_name": "Chase Bank",
    "quantity": 2,
    "unit_price": 150.0,
    "subtotal": 300.0,
    "discount_type": "Percentage",
    "discount_value": 10.0,
    "discount_amount": 30.0,
    "total_amount": 270.0,
    "status": "Active"
  }
}
```

**Discount Types:**
- **Percentage**: Value between 0-100 (e.g., 10 = 10% off)
- **Amount**: Fixed dollar amount (e.g., 25 = $25 off)

**Validation Rules:**
- Percentage must be ≤ 100%
- Amount must be ≤ subtotal
- Discount value must be ≥ 0
- User must have write permission on the Client Tradeline

#### POST `/rockettradeline.api.client_tradelines.remove_discount` 🔒
Remove discount from a Client Tradeline.

**Headers:** `X-Authorization: Bearer {token}`

**Request Body:**
```json
{
  "client_tradeline_id": "CTL-00001"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Discount removed successfully",
  "client_tradeline": {
    "name": "CTL-00001",
    "customer": "CUST-00001",
    "customer_name": "John Doe",
    "tradeline": "TL-0001",
    "tradeline_name": "Chase Bank",
    "quantity": 2,
    "unit_price": 150.0,
    "subtotal": 300.0,
    "discount_type": null,
    "discount_value": 0,
    "discount_amount": 0,
    "total_amount": 300.0,
    "status": "Active"
  }
}
```

---

### �👥 User Management APIs (Admin)

#### GET `/rockettradeline.api.auth.get_users` 🔒👑
Get list of users (Admin only).

**Headers:** `X-Authorization: Bearer {admin_token}`

**Parameters:**
- `limit` (int): Number of records (default: 20)
- `start` (int): Starting offset (default: 0)
- `search` (string): Search by email

**Response:**
```json
{
  "success": true,
  "users": [
    {
      "name": "user@example.com",
      "email": "user@example.com",
      "full_name": "John Doe",
      "enabled": true,
      "user_type": "Website User",
      "creation": "2025-08-17 01:00:00",
      "phone": "+1234567890",
      "customer": {
        "name": "CUST-00001",
        "customer_name": "John Doe",
        "customer_type": "Individual",
        "email_id": "user@example.com",
        "mobile_no": "+1234567890"
      }
    }
  ]
}
```

---

## 📋 Response Format

### Success Response
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": {...}
}
```

### Error Response
```json
{
  "success": false,
  "message": "Error description",
  "error_code": "SPECIFIC_ERROR_CODE",
  "details": {...}
}
```

## ⚠️ Error Codes

| Code | Description |
|------|-------------|
| `AUTHENTICATION_REQUIRED` | Valid authentication token required |
| `INVALID_TOKEN` | JWT token is invalid or expired |
| `EMAIL_NOT_VERIFIED` | Email address must be verified |
| `INSUFFICIENT_PERMISSIONS` | User lacks required permissions |
| `VALIDATION_ERROR` | Request data validation failed |
| `RESOURCE_NOT_FOUND` | Requested resource doesn't exist |
| `CART_EMPTY` | Operation requires non-empty cart |
| `PAYMENT_CONFIG_MISSING` | Payment method not configured |
| `RATE_LIMIT_EXCEEDED` | Too many requests |

## 🚦 Rate Limiting

- **Authentication endpoints**: 10 requests per minute
- **Cart operations**: 100 requests per minute
- **General endpoints**: 60 requests per minute

## 🛠️ SDKs & Examples

### JavaScript/Node.js Example

```javascript
// Authentication
const response = await fetch('https://rockettradeline.com/api/method/rockettradeline.api.auth.login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    usr: 'user@example.com',
    pwd: 'password123'
  })
});

const { authorization_token } = await response.json();

// Get tradelines
const tradelines = await fetch('https://rockettradeline.com/api/method/rockettradeline.api.tradeline.get_tradelines', {
  headers: {
    'X-Authorization': authorization_token
  }
});

// Add to cart
await fetch('https://rockettradeline.com/api/method/rockettradeline.api.cart.add_to_cart', {
  method: 'POST',
  headers: {
    'X-Authorization': authorization_token,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    tradeline_id: '00018',
    quantity: 1
  })
});
```

### Python Example

```python
import requests

# Authentication
login_response = requests.post(
    'https://rockettradeline.com/api/method/rockettradeline.api.auth.login',
    json={
        'usr': 'user@example.com',
        'pwd': 'password123'
    }
)

token = login_response.json()['authorization_token']

# Get tradelines
tradelines_response = requests.get(
    'https://rockettradeline.com/api/method/rockettradeline.api.tradeline.get_tradelines',
    headers={'X-Authorization': token}
)

# Add to cart
cart_response = requests.post(
    'https://rockettradeline.com/api/method/rockettradeline.api.cart.add_to_cart',
    headers={
        'X-Authorization': token,
        'Content-Type': 'application/json'
    },
    json={
        'tradeline_id': '00018',
        'quantity': 1
    }
)
```

### cURL Examples

```bash
# Login
curl -X POST "https://rockettradeline.com/api/method/rockettradeline.api.auth.login" \
  -H "Content-Type: application/json" \
  -d '{"usr":"user@example.com","pwd":"password123"}'

# Get tradelines
curl -X GET "https://rockettradeline.com/api/method/rockettradeline.api.tradeline.get_tradelines" \
  -H "X-Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Create cart
curl -X POST "https://rockettradeline.com/api/method/rockettradeline.api.cart.create_cart" \
  -H "X-Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json"

# Add to cart
curl -X POST "https://rockettradeline.com/api/method/rockettradeline.api.cart.add_to_cart" \
  -H "X-Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{"tradeline_id":"00018","quantity":1}'
```

## � Bulk Import System

### Overview
For administrators who need to import historical tradeline purchase data, RocketTradeLine provides a comprehensive **Tradeline Bulk Import** system. This allows you to import existing purchase records from Excel files without triggering customer email notifications.

### Key Features
- ✅ **Excel-based Import**: Upload purchases via Excel/CSV files
- ✅ **Complete Record Creation**: Automatically creates Customer, Cart, Payment Request, and Client Tradelines
- ✅ **Attachment Support**: Import proof of payment and AU assignment documents
- ✅ **Discount Support**: Import percentage and fixed-amount discounts
- ✅ **Email Suppression**: External imports don't trigger notifications
- ✅ **Data Validation**: Comprehensive validation of all import data
- ✅ **Status Preservation**: Maintains original payment and tradeline statuses

### Documentation
For complete details on the bulk import system, including:
- DocType structure and field definitions
- Excel template format
- `is_external` flag implementation
- Email suppression logic
- Step-by-step import process
- Validation rules and error handling

**See:** [TRADELINE_IMPORT_README.md](./TRADELINE_IMPORT_README.md)

### Quick Start
1. Download the Excel template (via admin panel)
2. Fill in purchase data with all required fields
3. Upload proof of payment and AU assignment files (optional)
4. Create new Tradeline Import record
5. Upload Excel file
6. Save to process the import
7. Review validation log and processing results

### Required Excel Columns
- Customer Email, Customer Name, Customer Phone
- Tradeline ID, Quantity, Unit Price
- Discount Type, Discount Value
- Cart Created Date, Payment Approved Date, AU Added Date
- Payment Status, Approval Status, Client Tradeline Status
- Expiry Date, Proof of Payment URL, Proof of AU URL

### Access Permissions
- **System Manager**: Full access to Tradeline Import
- **Administrator**: Full access to Tradeline Import
- **All other roles**: No access (admin-only feature)

---

## �📞 Support

For API support and questions:
- **Email**: support@rockettradeline.com
- **Documentation**: https://docs.rockettradeline.com
- **Status Page**: https://status.rockettradeline.com

---

## 📚 Additional Documentation

- **[Purchase Flow Documentation](./TRADELINE_PURCHASE_FLOW.md)** - Complete technical flow from cart to active tradeline
- **[Quick Reference Guide](./TRADELINE_QUICK_REFERENCE.md)** - API endpoints, validations, and cheat sheets
- **[Mermaid Diagrams](./TRADELINE_MERMAID_DIAGRAMS.md)** - Visual flowcharts and architecture diagrams
- **[Documentation Index](./DOCUMENTATION_INDEX.md)** - Navigation guide for all documentation
- **[Manual Import Guide](./TRADELINE_IMPORT_README.md)** - Complete import system documentation

---

## 📜 License

MIT License - see LICENSE file for details.

---

**🚀 Built with Frappe Framework | © 2025 Rocket Tradeline**

# JWT Authentication Decorators Guide

This guide explains how to use the JWT authentication decorators in the Rocket Tradeline API.

## Overview

The JWT authentication system provides two main decorators:
1. `@jwt_required()` - For protecting routes with JWT authentication
2. `@require_roles()` - For role-based access control

## Decorators

### `@jwt_required(allow_guest=False)`

Protects routes with JWT authentication and automatically sets `frappe.session.user`.

**Parameters:**
- `allow_guest` (bool): If True, allows guest access when no valid token is provided

**Features:**
- Validates JWT tokens from `Authorization: Bearer <token>` header
- Falls back to legacy API token format `Authorization: token api_key:api_secret`
- Automatically sets `frappe.session.user` to the authenticated user
- Returns 401 Unauthorized for invalid/missing tokens (unless `allow_guest=True`)

**Usage:**
```python
@frappe.whitelist(allow_guest=True)
@jwt_required()
def protected_endpoint():
    # frappe.session.user is automatically set
    return {"user": frappe.session.user}

@frappe.whitelist(allow_guest=True)
@jwt_required(allow_guest=True)
def optional_auth_endpoint():
    # Works with or without authentication
    if frappe.session.user != "Guest":
        return {"message": f"Hello {frappe.session.user}"}
    else:
        return {"message": "Hello Guest"}
```

### `@require_roles(*required_roles)`

Requires specific roles for accessing endpoints. Must be used with `@jwt_required()`.

**Parameters:**
- `required_roles` (str): One or more role names required for access

**Usage:**
```python
@frappe.whitelist(allow_guest=True)
@jwt_required()
@require_roles("System Manager", "Administrator")
def admin_endpoint():
    return {"message": "Admin access granted"}

@frappe.whitelist(allow_guest=True)
@jwt_required()
@require_roles("Customer")
def customer_endpoint():
    return {"message": "Customer access granted"}
```

## Authentication Flow

### 1. Login and Get JWT Token

```bash
curl -X POST \
  http://localhost:8000/api/method/rockettradeline.api.auth.login \
  -H "Content-Type: application/json" \
  -d '{
    "usr": "user@example.com",
    "pwd": "password"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Login successful",
  "authorization_token": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "Bearer",
  "expires_in": 86400,
  "user": {
    "name": "user@example.com",
    "email": "user@example.com",
    "full_name": "John Doe",
    "roles": ["Customer"]
  }
}
```

### 2. Use JWT Token in Requests

```bash
curl -X GET \
  http://localhost:8000/api/method/rockettradeline.api.auth.protected_endpoint \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

## Example Endpoints

The system includes example endpoints to demonstrate the decorators:

### 1. Protected Endpoint
- **URL:** `/api/method/rockettradeline.api.auth.protected_endpoint`
- **Auth:** Required (JWT)
- **Roles:** Any authenticated user

### 2. Optional Auth Endpoint
- **URL:** `/api/method/rockettradeline.api.auth.optional_auth_endpoint`
- **Auth:** Optional
- **Roles:** Any (including Guest)

### 3. Admin Only Endpoint
- **URL:** `/api/method/rockettradeline.api.auth.admin_only_endpoint`
- **Auth:** Required (JWT)
- **Roles:** System Manager or Administrator

## Updated API Endpoints

The following existing endpoints now use the JWT decorators:

### User Management
- `get_current_user()` - Uses `@jwt_required()`
- `update_profile()` - Uses `@jwt_required()`
- `refresh_token()` - Uses `@jwt_required()`

### Admin Endpoints
- `get_users()` - Uses `@jwt_required()` + `@require_roles("System Manager", "Administrator")`

## Error Responses

### 401 Unauthorized (Missing/Invalid Token)
```json
{
  "success": false,
  "message": "Authentication required"
}
```

### 403 Forbidden (Insufficient Role)
```json
{
  "success": false,
  "message": "Requires one of these roles: System Manager, Administrator"
}
```

## Token Security Features

1. **JWT with Payload**: Tokens contain user information and expiration
2. **Site-specific Secret**: Each site has its own JWT secret
3. **User Validation**: Checks if user exists and is enabled
4. **Role-based Access**: Fine-grained permission control
5. **Automatic Session Management**: Sets `frappe.session.user` automatically

## Best Practices

1. **Always use HTTPS** in production to protect tokens in transit
2. **Set appropriate token expiration** (default: 24 hours)
3. **Use role-based decorators** for fine-grained access control
4. **Handle token refresh** on the client side before expiration
5. **Log security events** for monitoring and debugging

## Migration from Legacy Auth

If you have existing endpoints using manual token validation, you can easily migrate:

**Before:**
```python
@frappe.whitelist()
def my_endpoint():
    user_name = validate_authorization_header()
    if not user_name:
        return {"error": "Not authenticated"}
    # ... rest of function
```

**After:**
```python
@frappe.whitelist(allow_guest=True)
@jwt_required()
def my_endpoint():
    # frappe.session.user is automatically set
    # ... rest of function
```

This provides cleaner code and consistent authentication handling across all endpoints.

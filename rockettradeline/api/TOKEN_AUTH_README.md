# Token-Based Authentication for Rocket Tradeline API

This implementation provides secure token-based authentication for the Rocket Tradeline API, following Frappe's REST API authentication standards.

## Overview

The API now supports two authentication methods:
1. **Session-based authentication** (for web browsers)
2. **Token-based authentication** (for API clients, mobile apps, etc.)

## Authentication Flow

### 1. Registration/Login

When a user registers or logs in, they receive API tokens:

```json
{
  "success": true,
  "message": "Login successful",
  "token": "token abcd1234567890:xyz9876543210abcdef",
  "api_key": "abcd1234567890",
  "api_secret": "xyz9876543210abcdef",
  "user": { ... },
  "customer": { ... }
}
```

### 2. Using Tokens for API Calls

Include the token in the `Authorization` header:

```bash
curl -X GET \
  https://staging.rockettradline.com/api/method/rockettradeline.api.auth.get_current_user \
  -H "Authorization: token abcd1234567890:xyz9876543210abcdef"
```

## API Endpoints

### Authentication Endpoints

#### 1. Login
```
POST /api/method/rockettradeline.api.auth.login
```

**Request Body:**
```json
{
  "usr": "user@example.com",
  "pwd": "password123"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Login successful",
  "token": "token api_key:api_secret",
  "api_key": "your_api_key",
  "api_secret": "your_api_secret",
  "user": {
    "name": "user@example.com",
    "email": "user@example.com",
    "full_name": "John Doe",
    "user_image": "/files/user_image.jpg",
    "phone": "+1234567890",
    "role_profile_name": "Customer",
    "roles": ["Customer"]
  },
  "customer": {
    "name": "CUST-00001",
    "customer_name": "John Doe",
    "customer_type": "Individual",
    "email_id": "user@example.com",
    "mobile_no": "+1234567890",
    "territory": "All Territories"
  }
}
```

#### 2. Sign Up
```
POST /api/method/rockettradeline.api.auth.sign_up
```

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "full_name": "Jane Doe",
  "password": "securepassword123",
  "phone": "+1234567890"
}
```

**Response:** Same format as login

#### 3. Validate Token
```
GET /api/method/rockettradeline.api.auth.validate_token
```

**Headers:**
```
Authorization: token api_key:api_secret
```

**Response:**
```json
{
  "success": true,
  "valid": true,
  "user": { ... },
  "customer": { ... }
}
```

### Token Management Endpoints

#### 4. Get Current Tokens
```
GET /api/method/rockettradeline.api.auth.get_tokens
```

**Headers:**
```
Authorization: token api_key:api_secret
```

**Response:**
```json
{
  "success": true,
  "token": "token api_key:api_secret",
  "api_key": "your_api_key",
  "api_secret": "your_api_secret"
}
```

#### 5. Regenerate Tokens
```
POST /api/method/rockettradeline.api.auth.regenerate_tokens
```

**Headers:**
```
Authorization: token api_key:api_secret
```

**Response:**
```json
{
  "success": true,
  "message": "New tokens generated successfully",
  "token": "token new_api_key:new_api_secret",
  "api_key": "new_api_key",
  "api_secret": "new_api_secret"
}
```

#### 6. Revoke Tokens
```
POST /api/method/rockettradeline.api.auth.revoke_tokens
```

**Headers:**
```
Authorization: token api_key:api_secret
```

**Response:**
```json
{
  "success": true,
  "message": "Tokens revoked successfully"
}
```

### User Profile Endpoints

#### 7. Get Current User
```
GET /api/method/rockettradeline.api.auth.get_current_user
```

**Headers:**
```
Authorization: token api_key:api_secret
```

#### 8. Update Profile
```
POST /api/method/rockettradeline.api.auth.update_profile
```

**Headers:**
```
Authorization: token api_key:api_secret
```

**Request Body:**
```json
{
  "full_name": "John Updated Doe",
  "phone": "+1987654321",
  "user_image": "/files/new_image.jpg"
}
```

## Frontend Integration Examples

### JavaScript/React Example

```javascript
class RocketTradelineAPI {
  constructor(baseURL) {
    this.baseURL = baseURL;
    this.token = localStorage.getItem('api_token');
  }

  setToken(token) {
    this.token = token;
    localStorage.setItem('api_token', token);
  }

  clearToken() {
    this.token = null;
    localStorage.removeItem('api_token');
  }

  async apiCall(endpoint, method = 'GET', data = null) {
    const headers = {
      'Content-Type': 'application/json',
    };

    if (this.token) {
      headers['Authorization'] = this.token;
    }

    const config = {
      method,
      headers,
    };

    if (data) {
      config.body = JSON.stringify(data);
    }

    const response = await fetch(`${this.baseURL}/api/method/${endpoint}`, config);
    return response.json();
  }

  async login(email, password) {
    const result = await this.apiCall('rockettradeline.api.auth.login', 'POST', {
      usr: email,
      pwd: password
    });

    if (result.success) {
      this.setToken(result.token);
    }

    return result;
  }

  async getCurrentUser() {
    return this.apiCall('rockettradeline.api.auth.get_current_user');
  }

  async updateProfile(profileData) {
    return this.apiCall('rockettradeline.api.auth.update_profile', 'POST', profileData);
  }

  async logout() {
    const result = await this.apiCall('rockettradeline.api.auth.logout', 'POST');
    this.clearToken();
    return result;
  }
}

// Usage
const api = new RocketTradelineAPI('https://staging.rockettradline.com');

// Login
const loginResult = await api.login('user@example.com', 'password123');
if (loginResult.success) {
  console.log('Logged in successfully!', loginResult.user);
}

// Get current user
const userResult = await api.getCurrentUser();
if (userResult.success) {
  console.log('Current user:', userResult.user);
}
```

### Python Example

```python
import requests

class RocketTradelineAPI:
    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None

    def set_token(self, token):
        self.token = token

    def _make_request(self, endpoint, method='GET', data=None):
        url = f"{self.base_url}/api/method/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if self.token:
            headers['Authorization'] = self.token
        
        if method == 'GET':
            response = requests.get(url, headers=headers)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data)
        
        return response.json()

    def login(self, email, password):
        result = self._make_request('rockettradeline.api.auth.login', 'POST', {
            'usr': email,
            'pwd': password
        })
        
        if result.get('success'):
            self.set_token(result.get('token'))
        
        return result

    def get_current_user(self):
        return self._make_request('rockettradeline.api.auth.get_current_user')

    def update_profile(self, **profile_data):
        return self._make_request('rockettradeline.api.auth.update_profile', 'POST', profile_data)

# Usage
api = RocketTradelineAPI('https://staging.rockettradline.com')

# Login
login_result = api.login('user@example.com', 'password123')
if login_result.get('success'):
    print('Logged in successfully!', login_result.get('user'))

# Get current user
user_result = api.get_current_user()
if user_result.get('success'):
    print('Current user:', user_result.get('user'))
```

## Security Best Practices

1. **Store tokens securely**: Never store tokens in plain text or localStorage in production
2. **Use HTTPS**: Always use HTTPS in production to encrypt token transmission
3. **Token rotation**: Regularly regenerate tokens for enhanced security
4. **Revoke compromised tokens**: Immediately revoke tokens if suspected of being compromised
5. **Validate tokens**: Always validate tokens on the server side before processing requests

## Error Handling

All endpoints return standardized error responses:

```json
{
  "success": false,
  "message": "Error description"
}
```

Common HTTP status codes:
- `200`: Success
- `400`: Bad Request (invalid input)
- `401`: Unauthorized (invalid/missing token)
- `403`: Forbidden (insufficient permissions)
- `409`: Conflict (user already exists)
- `500`: Internal Server Error

## Token Format

Tokens follow the format: `token api_key:api_secret`

Example: `token abcd1234567890:xyz9876543210abcdef`

This format is compatible with Frappe's standard REST API authentication system.

#!/usr/bin/env python3
"""
Test script for User-Customer integration
"""
import json
import requests
import sys

# Configuration
BASE_URL = "https://rockettradline.com/api/method/rockettradeline.api.auth"
# For local testing, use:
# BASE_URL = "http://localhost:8000/api/method/rockettradeline.api.auth"

def test_user_signup_with_customer():
    """Test user signup with customer creation"""
    url = f"{BASE_URL}.sign_up"
    
    test_data = {
        "email": "testuser@example.com",
        "full_name": "Test User",
        "password": "password123",
        "phone": "+1-555-123-4567"
    }
    
    print("Testing user signup with customer creation...")
    response = requests.post(url, json=test_data)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Status: {data.get('success')}")
        print(f"✓ Message: {data.get('message')}")
        print(f"✓ User: {data.get('user')}")
        print(f"✓ Customer: {data.get('customer')}")
    else:
        print(f"✗ Error: {response.status_code}")
        print(f"✗ Response: {response.text}")
    
    print("-" * 50)

def test_user_login_with_customer():
    """Test user login with customer information"""
    url = f"{BASE_URL}.login"
    
    test_data = {
        "usr": "testuser@example.com",
        "pwd": "password123"
    }
    
    print("Testing user login with customer information...")
    response = requests.post(url, json=test_data)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Status: {data.get('success')}")
        print(f"✓ Message: {data.get('message')}")
        print(f"✓ User: {data.get('user')}")
        print(f"✓ Customer: {data.get('customer')}")
        
        # Store session for subsequent requests
        return response.cookies
    else:
        print(f"✗ Error: {response.status_code}")
        print(f"✗ Response: {response.text}")
    
    print("-" * 50)
    return None

def test_get_current_user_with_customer(cookies):
    """Test getting current user with customer information"""
    if not cookies:
        print("No session cookies available, skipping test...")
        return
    
    url = f"{BASE_URL}.get_current_user"
    
    print("Testing get current user with customer information...")
    response = requests.get(url, cookies=cookies)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Status: {data.get('success')}")
        print(f"✓ User: {data.get('user')}")
        print(f"✓ Customer: {data.get('customer')}")
    else:
        print(f"✗ Error: {response.status_code}")
        print(f"✗ Response: {response.text}")
    
    print("-" * 50)

def test_update_profile_with_customer(cookies):
    """Test updating profile with customer sync"""
    if not cookies:
        print("No session cookies available, skipping test...")
        return
    
    url = f"{BASE_URL}.update_profile"
    
    test_data = {
        "full_name": "Updated Test User",
        "phone": "+1-555-999-8888"
    }
    
    print("Testing profile update with customer sync...")
    response = requests.post(url, json=test_data, cookies=cookies)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Status: {data.get('success')}")
        print(f"✓ Message: {data.get('message')}")
        print(f"✓ User: {data.get('user')}")
        print(f"✓ Customer: {data.get('customer')}")
    else:
        print(f"✗ Error: {response.status_code}")
        print(f"✗ Response: {response.text}")
    
    print("-" * 50)

def test_create_customer_for_existing_user():
    """Test creating customer for existing user (Admin function)"""
    url = f"{BASE_URL}.create_customer_for_user"
    
    test_data = {
        "user_email": "existing@example.com"
    }
    
    print("Testing create customer for existing user...")
    response = requests.post(url, json=test_data)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Status: {data.get('success')}")
        print(f"✓ Message: {data.get('message')}")
        print(f"✓ Customer: {data.get('customer')}")
    else:
        print(f"✗ Error: {response.status_code}")
        print(f"✗ Response: {response.text}")
    
    print("-" * 50)

def test_get_users_with_customer_info():
    """Test getting users with customer information"""
    url = f"{BASE_URL}.get_users"
    
    print("Testing get users with customer information...")
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Status: {data.get('success')}")
        users = data.get('users', [])
        print(f"✓ Users count: {len(users)}")
        if users:
            print(f"✓ First user: {users[0]}")
    else:
        print(f"✗ Error: {response.status_code}")
        print(f"✗ Response: {response.text}")
    
    print("-" * 50)

def main():
    """Run all tests"""
    print("User-Customer Integration Test Suite")
    print("=" * 50)
    
    # Test sequence
    test_user_signup_with_customer()
    cookies = test_user_login_with_customer()
    test_get_current_user_with_customer(cookies)
    test_update_profile_with_customer(cookies)
    test_create_customer_for_existing_user()
    test_get_users_with_customer_info()
    
    print("Test suite completed!")

if __name__ == "__main__":
    main()

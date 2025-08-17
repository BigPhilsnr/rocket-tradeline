#!/usr/bin/env python3
"""
Test script for Site Content API
"""
import json
import requests
import sys

# Configuration
BASE_URL = "https://rockettradline.com/api/method/rockettradeline.api.website"
# For local testing, use:
# BASE_URL = "http://localhost:8000/api/method/rockettradeline.api.website"

def test_set_site_content():
    """Test setting site content"""
    url = f"{BASE_URL}.set_site_content"
    
    test_data = {
        "key": "hero_title",
        "value": "Boost Your Credit Score with Our Tradelines",
        "section": "hero",
        "page": "landing",
        "content_type": "Text"
    }
    
    print("Testing set_site_content...")
    response = requests.post(url, json=test_data)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Status: {data.get('success')}")
        print(f"✓ Message: {data.get('message')}")
        print(f"✓ Content: {data.get('content')}")
    else:
        print(f"✗ Error: {response.status_code}")
        print(f"✗ Response: {response.text}")
    
    print("-" * 50)

def test_get_content_by_key():
    """Test getting content by key"""
    url = f"{BASE_URL}.get_content_by_key"
    
    print("Testing get_content_by_key...")
    response = requests.get(url, params={"key": "hero_title"})
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Status: {data.get('success')}")
        print(f"✓ Key: {data.get('key')}")
        print(f"✓ Value: {data.get('value')}")
        print(f"✓ Content Type: {data.get('content_type')}")
    else:
        print(f"✗ Error: {response.status_code}")
        print(f"✗ Response: {response.text}")
    
    print("-" * 50)

def test_get_site_content():
    """Test getting site content with filters"""
    url = f"{BASE_URL}.get_site_content"
    
    print("Testing get_site_content with section and page...")
    response = requests.get(url, params={
        "section": "hero", 
        "page": "landing"
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Status: {data.get('success')}")
        print(f"✓ Content count: {len(data.get('content', []))}")
        if data.get('content'):
            print(f"✓ First item: {data['content'][0]}")
    else:
        print(f"✗ Error: {response.status_code}")
        print(f"✗ Response: {response.text}")
    
    print("-" * 50)

def test_bulk_set_site_content():
    """Test bulk setting site content"""
    url = f"{BASE_URL}.bulk_set_site_content"
    
    test_data = {
        "content_list": [
            {
                "key": "hero_subtitle",
                "value": "Get authorized user tradelines from premium accounts",
                "section": "hero",
                "page": "landing",
                "content_type": "Text"
            },
            {
                "key": "hero_cta",
                "value": "Get Started Today",
                "section": "hero",
                "page": "landing",
                "content_type": "Text"
            }
        ]
    }
    
    print("Testing bulk_set_site_content...")
    response = requests.post(url, json=test_data)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Status: {data.get('success')}")
        print(f"✓ Message: {data.get('message')}")
        print(f"✓ Results: {len(data.get('results', []))}")
        print(f"✓ Errors: {len(data.get('errors', []))}")
    else:
        print(f"✗ Error: {response.status_code}")
        print(f"✗ Response: {response.text}")
    
    print("-" * 50)

def test_legacy_website_settings():
    """Test legacy website settings API"""
    url = f"{BASE_URL}.get_website_settings"
    
    print("Testing legacy get_website_settings...")
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Status: {data.get('success')}")
        print(f"✓ Settings: {data.get('settings')}")
    else:
        print(f"✗ Error: {response.status_code}")
        print(f"✗ Response: {response.text}")
    
    print("-" * 50)

def main():
    """Run all tests"""
    print("Site Content API Test Suite")
    print("=" * 50)
    
    # Test sequence
    test_set_site_content()
    test_get_content_by_key()
    test_bulk_set_site_content()
    test_get_site_content()
    test_legacy_website_settings()
    
    print("Test suite completed!")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Simple GameMasterJJ Test Script
"""

import requests
import json

def test_combat():
    """Test combat scenario"""
    print("=== COMBAT TEST ===")

    payload = {
        "content": "A goblin attacks me! I attack with my sword",
        "user_id": "test-player"
    }

    response = requests.post(
        "http://localhost:8000/api/v1/sessions/combat-test/messages",
        json=payload
    )

    result = response.json()
    print(f"Agent: {result['agent']}")
    print(f"Message: {result['message'][:200]}...")
    print()

def test_magic():
    """Test magic scenario"""
    print("=== MAGIC TEST ===")

    payload = {
        "content": "I cast magic missile at the orc",
        "user_id": "test-player"
    }

    response = requests.post(
        "http://localhost:8000/api/v1/sessions/magic-test/messages",
        json=payload
    )

    result = response.json()
    print(f"Agent: {result['agent']}")
    print(f"Message: {result['message'][:200]}...")
    print()

def test_social():
    """Test social interaction"""
    print("=== SOCIAL TEST ===")

    payload = {
        "content": "I try to persuade the guard to let me pass",
        "user_id": "test-player"
    }

    response = requests.post(
        "http://localhost:8000/api/v1/sessions/social-test/messages",
        json=payload
    )

    result = response.json()
    print(f"Agent: {result['agent']}")
    print(f"Message: {result['message'][:200]}...")
    print()

def test_exploration():
    """Test exploration"""
    print("=== EXPLORATION TEST ===")

    payload = {
        "content": "I search the room for secret doors",
        "user_id": "test-player"
    }

    response = requests.post(
        "http://localhost:8000/api/v1/sessions/explore-test/messages",
        json=payload
    )

    result = response.json()
    print(f"Agent: {result['agent']}")
    print(f"Message: {result['message'][:200]}...")
    print()

def test_lore():
    """Test lore request"""
    print("=== LORE TEST ===")

    payload = {
        "content": "Tell me about the ancient dragon lords",
        "user_id": "test-player"
    }

    response = requests.post(
        "http://localhost:8000/api/v1/sessions/lore-test/messages",
        json=payload
    )

    result = response.json()
    print(f"Agent: {result['agent']}")
    print(f"Message: {result['message'][:200]}...")
    print()

if __name__ == "__main__":
    print("GameMasterJJ Test Suite")
    print("======================")

    try:
        # Check server
        response = requests.get("http://localhost:8000/api/v1/health")
        print("Server Status: OK")
        print()

        # Run tests
        test_combat()
        test_magic()
        test_social()
        test_exploration()
        test_lore()

        print("All tests completed!")

    except Exception as e:
        print(f"Error: {str(e)}")
        print("Make sure the server is running: python start.py")
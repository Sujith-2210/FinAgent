"""
Test Script for FinAgent Improvements
Tests the 5 key scenarios mentioned in the implementation plan.
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_query(query: str, test_name: str):
    """Send a query to the backend and display results."""
    print(f"\n{'='*80}")
    print(f"TEST: {test_name}")
    print(f"Query: {query}")
    print(f"{'='*80}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/chat/",
            json={
                "message": query,
                "session_id": "test-improvements"
            },
            timeout=120
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✓ Status: {response.status_code}")
            
            # Debug: print raw response structure
            # print(f"\n🔍 Raw response keys: {list(data.keys())}")
            
            # The API returns 'message' not 'summary'
            message = data.get('message', 'No message available')
            
            print(f"\n📝 Response:")
            print(f"{message[:600]}..." if len(message) > 600 else message)
            
            # Check for actions (images)
            actions = data.get('actions', [])
            if actions:
                print(f"\n📊 Actions/Charts: {len(actions)} item(s)")
                for action in actions:
                    if isinstance(action, dict):
                        print(f"  - {action.get('type', 'chart')}: {action.get('description', 'Generated chart')}")
            
            # Show agents used
            agents = data.get('agents_involved', [])
            if agents:
                print(f"\n🤖 Agents Used: {', '.join(agents)}")
            
            return True
        else:
            print(f"\n✗ Error: {response.status_code}")
            print(response.text[:500])
            return False
            
    except Exception as e:
        print(f"\n✗ Exception: {e}")
        return False

def main():
    print("="*80)
    print("FinAgent Improvements - Test Suite")
    print("="*80)
    
    # Check if backend is running
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"\n✓ Backend is running (status: {health.status_code})")
    except:
        print("\n✗ Backend is not running!")
        print("\nPlease start the backend with:")
        print("cd /Users/sujith/Documents/FinAgent/New/backend")
        print("python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        return
    
    time.sleep(1)
    
    # Test 1: House Purchase Query
    test_query(
        "i want to purchase a house which is a worth of 10cr and for the loan how much credit score should i have?",
        "House Purchase with Credit Score Calculation"
    )
    time.sleep(2)
    
    # Test 2: Tesla Stock Prediction
    test_query(
        "generate a chart of predicting the stock price of Tesla for next month",
        "Tesla Stock Prediction (Should use TSLA ticker)"
    )
    time.sleep(2)
    
    # Test 3: User Age Query
    test_query(
        "Tell the present Age of me",
        "User Age Extraction from MCP"
    )
    time.sleep(2)
    
    # Test 4: Historical Stock Downfall
    test_query(
        "what's the worst downfall stock in it's history?",
        "Historical Analysis with Web Data"
    )
    time.sleep(2)
    
    # Test 5: Investor Comparison
    test_query(
        "who invested more money on stocks",
        "Investor Comparison with Web Search"
    )
    
    print(f"\n{'='*80}")
    print("Test Suite Complete!")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()

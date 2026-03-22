import requests
import json
import time

def verify_prediction():
    url = "http://localhost:8000/api/chat/"
    payload = {
        "message": "Predict HDFC Bank stock price for the next month",
        "session_id": "test-session-1"
    }
    
    print(f"Sending request to {url}...")
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        print("\nResponse Status:", response.status_code)
        # print(json.dumps(data, indent=2))
        
        # Check for key fields
        print("\nVerification Results:")
        
        # 1. Check for explanation in message
        if data.get("message"):
            print("✅ Message received")
        else:
            print("❌ No message received")
            
        # 2. Check for actions (Success indicator for code agent)
        actions = data.get("actions", [])
        if actions:
            print(f"✅ Actions received: {len(actions)}")
            for action in actions:
                print(f"   - Type: {action.get('type')}")
                if action.get('type') == 'image':
                    print("   - Image data present")
        else:
            print("⚠️ No actions/images received (Code extraction might have failed or plain answer returned)")

        # 3. Check agents involved
        agents = data.get("agents_involved", [])
        print(f"✅ Agents involved: {agents}")
        if "code" in agents:
            print("✅ Code agent was invoked")
        else:
            print("❌ Code agent was NOT invoked")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Wait for server to start
    print("Waiting for server to start...")
    time.sleep(5) 
    verify_prediction()

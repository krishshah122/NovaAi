import requests
import json
import time

url = "https://darwixai-assignement.onrender.com/webhook/vapi"
payload = {
    "message": {
        "type": "toolCalls",
        "toolCallList": [
            {
                "id": "call_12345",
                "type": "function",
                "function": {
                    "name": "query_knowledge_base",
                    "arguments": json.dumps({"question": "Can you tell me about Nova Platinum Health Plus plan?"})
                }
            }
        ]
    }
}

print(f"Sending POST to {url}...")
start = time.time()
try:
    res = requests.post(url, json=payload)
    end = time.time()
    print(f"Status Code: {res.status_code}")
    print(f"Latency: {end - start:.2f} seconds")
    try:
        print("Response JSON:")
        print(json.dumps(res.json(), indent=2))
    except:
        print("Response Text:")
        print(res.text)
except Exception as e:
    print(f"Error: {e}")

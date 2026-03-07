import requests
import json

url = "http://127.0.0.1:8000/customer/ChatView/"
payload = {
    "tenant_id": "DMC",
    "conversation_id": "coWWDD34AW5WddWD_wwws1234ss5",
    "employee_id": "obinna.kelechi.adewale@dignityconcept.tech",
    "message_content": "Give me the monthly transaction count from inception use chart to illustrate ?",
    "summarization_request": False
}

response = requests.post(url, json=payload)

print("Status Code:", response.status_code)
print("Response:")
print(response.text)

if response.status_code == 200:
    data = response.json()
    answer = data.get("answer", "")
    print("Answer contains visualization:")
    if "chart" in answer.lower() or "visual" in answer.lower() or "plot" in answer.lower():
        print("Yes, the response includes visualization content.")
    else:
        print("No, the response does not mention visualization.")
else:
    print("Request failed.")
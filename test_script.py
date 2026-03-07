import requests
import json

url = "http://127.0.0.1:8000/customer/ChatView/"
payload = {
    "tenant_id": "DMC",
    "conversation_id": "coWWDD34AW5WWD_wwwssss1234ss5",
    "employee_id": "obinna.kelechi.adewale@dignityconcept.tech",
    "message_content": "Give me the monthly transaction count from inception use chart to illustrate ?",
    "summarization_request": False
}
headers = {'Content-type': 'application/json'}

print("Sending POST request to ChatView...")
response = requests.post(url, data=json.dumps(payload), headers=headers)
print(f"Response status: {response.status_code}")
print("Response text:")
print(response.text)

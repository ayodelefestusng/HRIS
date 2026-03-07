import requests

url = "http://127.0.0.1:8000/customer/ChatView/"
payload = {
  "tenant_id": "DMC",
  "conversation_id": "coWWDD34AW5WddWD_wwws1234ss5",
  "employee_id": "obinna.kelechi.adewale@dignityconcept.tech",
  "message_content": "Give me the monthly transaction count from inception use chart to illustrate ?",
  "summarization_request": False
}

try:
    response = requests.post(url, json=payload)
    print("Status Code:", response.status_code)
    try:
        print("Response JSON:", response.json())
    except:
        print("Response Text:", response.text)
except requests.exceptions.RequestException as e:
    print("Error:", e)

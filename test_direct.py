import os
import django
import sys
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from customer.chat_bot import process_message

for i in range(2):
    print(f"starting process_message {i}...")
    try:
        process_message(
            message_content=f"Give me the monthly transaction count from inception use chart to illustrate ? {i}",
            conversation_id=f"coWWDD34AW5WddWD_wwws1234ss{i}",
            tenant_id="DMC",
            employee_id="obinna.kelechi.adewale@dignityconcept.tech",
            summarization_request=False
        )
        print(f"FINISHED {i}")
    except Exception as e:
        print(traceback.format_exc())

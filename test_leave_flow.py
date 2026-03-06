import os
import sys
import django

# 1. Setup the project path
sys.path.append(os.getcwd())

# 2. Tell Django where your settings are
# Replace 'myproject.settings' with the actual path if different
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

# 3. Initialize Django
django.setup()

# --- Now you can import your bot logic ---
try:
    from customer.chat_bot import ChatBot
    print("✅ Django initialized and ChatBot imported.")
except Exception as e:
    print(f"❌ Initialization error: {e}")

# ... (rest of the simulation code from before)
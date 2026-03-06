# gravity

import os
import sys
import django

# 1. Setup Environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings') # Verify this is your settings path
try:
    django.setup()
except Exception as e:
    print(f"⚠️ Django setup warning: {e} (Continuing anyway...)")

# 2. Import the specific function we found
try:
    from customer.chat_bot import process_message
    print("✅ Successfully imported process_message")
except ImportError as e:
    print(f"❌ Import Error: {e}")
    sys.exit()

def test_logic_flow():
    print("\n--- Testing 'leave_application' Logic ---")
    
    # We aren't going to run the whole LLM (which takes time/API keys)
    # We are going to test if the variable mapping we saw in the file exists.
    
    import inspect
    source = inspect.getsource(process_message)
    
    if "leave_application" in source and "output.get" in source:
        print("🎯 CONFIRMED: The source code of process_message uses 'leave_application'.")
        
        # Look for the specific line to show the user
        lines = source.splitlines()
        for i, line in enumerate(lines):
            if "leave_application" in line:
                print(f"Found at line {i}: {line.strip()}")
    else:
        print("❌ WARNING: The string 'leave_application' was not found inside the process_message function.")

if __name__ == "__main__":
    test_logic_flow()
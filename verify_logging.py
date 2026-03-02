import os
import django
import logging

# Setup Django configuration
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

def verify_logging():
    print("Verifying logging configuration...")
    
    # Get loggers
    debug_logger = logging.getLogger('hr')
    error_logger = logging.getLogger('django')
    
    # Log messages
    debug_logger.debug("Test DEBUG message from verification script.")
    error_logger.error("Test ERROR message from verification script.")
    
    print("Messages sent. Please check 'logs/debug.log' and 'logs/error.log'.")

if __name__ == "__main__":
    verify_logging()

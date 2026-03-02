import requests
from django.conf import settings


def post_to_google_chat(webhook_url: str, text: str):
    payload = {"text": text}
    requests.post(webhook_url, json=payload, timeout=5)


def notify_role_fit(employee, role_fit):
    """
    Sends a simple message about role fit to a configured Google Chat space.
    """
    webhook_url = getattr(settings, "GOOGLE_CHAT_WEBHOOK_URL", None)
    if not webhook_url:
        return

    text = (
        f"Role fit update:\n"
        f"Employee: {employee}\n"
        f"Role: {role_fit.role.name}\n"
        f"Fit Score: {role_fit.score}%"
    )
    post_to_google_chat(webhook_url, text)
    
    
import requests
from django.conf import settings


def post_to_google_chat(text: str):
    webhook_url = getattr(settings, "GOOGLE_CHAT_WEBHOOK_URL", None)
    if not webhook_url:
        return
    try:
        requests.post(webhook_url, json={"text": text}, timeout=5)
    except Exception:
        # swallow errors – we don't want app flow to break due to chat issues
        pass
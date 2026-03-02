from django.urls import path
from . import views

app_name = "hr"

urlpatterns = [
    # Homepage / Dashboard
    path("", views.index, name="index"),
    # Bot API
    path("send-message/", views.send_message, name="send_message"),
    # Legacy / Additional Support
    path("chat/", views.chat_home, name="chat_home"),
    # Admin
    path("admin-tool/", views.admin_tool, name="admin_tool"),
]

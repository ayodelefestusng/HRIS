from django.urls import path
from . import views
app_name = 'core'
urlpatterns = [
    
    path('global-search/', views.global_search, name='global_search'),
    path('core/toggle-mode/', views.toggle_mode, name='toggle_mode'),
    
    # path('subscription/', views.billing_dashboard, name='billing_dashboard'),
    # path('invoice/<int:pk>/pay/', views.process_payment, name='process_payment'),
    # path('super-admin/health/', views_admin.system_health_dashboard, name='system_health'),
    # path('super-admin/logs/export/', views_admin.export_audit_logs, name='export_logs'),
]

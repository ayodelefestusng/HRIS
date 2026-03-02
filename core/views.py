from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .services import GlobalSearchService
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import user_passes_test
from org.models import Tenant
from employees.models import Employee
from .models import GlobalAuditLog
from django.db.models import Count,Max

# Create your views here.
@login_required
def global_search(request):
    query = request.GET.get('q', '')
    results = GlobalSearchService.search(request.tenant, query)
    
    # We return a partial specifically for the dropdown
    return render(request, 'core/partials/_search_results.html', results)



@require_POST
def toggle_mode(request):
    """
    Toggles between 'slate' (Dark) and 'light' modes using sessions.
    """
    current_mode = request.session.get('ui_mode', 'slate')
    new_mode = 'light' if current_mode == 'slate' else 'slate'
    request.session['ui_mode'] = new_mode
    
    # We trigger a page reload via HTMX header so the new CSS applies
    response = HttpResponse()
    response['HX-Refresh'] = 'true'
    return response

@user_passes_test(lambda u: u.is_superuser)
def system_health_dashboard(request):
    # 1. Platform Metrics
    context = {
        'total_tenants': Tenant.objects.count(),
        'active_employees': Employee.objects.filter(status='ACTIVE').count(),
        'failed_tasks': 0, # Integrate with Celery/Flower API in production
        'audit_logs': GlobalAuditLog.objects.all()[:50],
        'tenant_stats': Tenant.objects.annotate(
            emp_count=Count('employees'),
            last_login=Max('employees__user__last_login')
        )
    }
    return render(request, 'core/admin/health_dashboard.html', context)

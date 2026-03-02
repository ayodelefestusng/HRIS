def log_security_event(request, module, action, description):
    """
    Utility to capture security-sensitive events globally.
    """
    GlobalAuditLog.objects.create(
        tenant=getattr(request, 'tenant', None),
        user=request.user,
        module=module,
        action=action,
        description=description,
        ip_address=request.META.get('REMOTE_ADDR')
    )
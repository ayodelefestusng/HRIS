def user_mode_processor(request):
    if request.user.is_authenticated:
        # Default to 'employee' if not set
        mode = getattr(request.user.profile, 'preferred_mode', 'employee')
        return {
            'current_mode': mode,
            'body_class': 'mode-admin' if mode == 'admin' else 'mode-employee'
        }
    return {}
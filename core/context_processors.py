from org.models import Tenant

def tenant_branding(request):
    """
    Context processor to inject tenant-specific branding data into templates.
    """
    # Default system settings
    branding = {
        'logo_url': None,
        'favicon_url': None,
        'primary_color': '#4f46e5',
        'secondary_color': '#6366f1',
        'font_family': "'Inter', sans-serif",
        'tenant_name': 'HRMS'
    }
    
    tenant = None
    
    # 1. Resolve tenant via authenticated user
    if request.user.is_authenticated:
        tenant = getattr(request.user, 'tenant', None)
    
    # 2. Add resolution for public pages here if needed (e.g., subdomain)
    # if not tenant:
    #     host = request.get_host().split(':')[0]
    #     tenant = Tenant.objects.filter(subdomain=host).first()

    if tenant:
        branding['logo_url'] = tenant.logo.url if tenant.logo else None
        branding['favicon_url'] = tenant.favicon.url if tenant.favicon else None
        branding['primary_color'] = tenant.primary_color
        branding['secondary_color'] = tenant.secondary_color
        branding['font_family'] = tenant.font_family
        branding['tenant_name'] = tenant.name
        branding['custom_css'] = tenant.custom_css
        branding['brand_name'] = tenant.brand_name
        # Convert hex to RGB for CSS rgba() usage
        hex_color = tenant.primary_color.lstrip('#')
        if len(hex_color) == 6:
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            branding['primary_color_rgb'] = f"{r}, {g}, {b}"
        
    return {'branding': branding}

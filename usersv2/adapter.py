from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        print("Extra data from social login:", sociallogin.account.extra_data)
        user = super().populate_user(request, sociallogin, data)
        full_name = data.get('name') or f"{data.get('given_name', '')} {data.get('family_name', '')}".strip()
        user.full_name = full_name
        return user
    
    
    def pre_social_login(self, request, sociallogin):
        # If user is already logged in, do nothing
        if request.user.is_authenticated:
            return

        # Try to find existing user by email
        email = sociallogin.account.extra_data.get('email')
        if email:
            from users.models import User  # or wherever your custom user model is
            try:
                user = User.objects.get(email=email)
                sociallogin.connect(request, user)
            except User.DoesNotExist:
                pass

    def get_login_redirect_url(self, request):
        next_url = request.POST.get('next') or request.GET.get('next')
        if next_url:
            return next_url
        return super().get_login_redirect_url(request)

    def save_user(self, request, sociallogin, form=None):
        user = sociallogin.user
        extra_data = sociallogin.account.extra_data
        full_name = extra_data.get('name') or f"{extra_data.get('given_name', '')} {extra_data.get('family_name', '')}".strip()

        if not user.full_name:
            user.full_name = full_name

        user.save()
        return user

    def is_open_for_signup(self, request, sociallogin):
        print("Extra data:", sociallogin.account.extra_data)
        name = sociallogin.account.extra_data.get('name') or ''
        return bool(name.strip())
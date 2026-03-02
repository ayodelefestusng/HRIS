from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _





class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        # if not extra_fields.get('tenant'):
        #     raise ValueError("Superuser must have a tenant")

        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        


        # if not extra_fields.get('is_staff'):
        #     raise ValueError('Superuser must have is_staff=True.')
        # if not extra_fields.get('is_superuser'):
        #     raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    username = None  # 👈 Explicitly remove username field
    tenant = models.ForeignKey(
    'org.Tenant',
    on_delete=models.PROTECT,
     null=True,      # allow NULL
        blank=True

)


    email = models.EmailField(unique=True)
    full_name = models.CharField(_('full name'), max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    is_seller = models.BooleanField(default=False)
    is_buyer = models.BooleanField(default=True)

    mfa_secret = models.CharField(max_length=16, blank=True, null=True)
    mfa_enabled = models.BooleanField(default=False)
    

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='myapp_users',
        blank=True,
        help_text='The groups this user belongs to.'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='myapp_user_permissions',
        blank=True,
        help_text='Specific permissions for this user.'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    objects = CustomUserManager()
    # Add this to your User model in user/models.py

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'


# apps/core/models.py
from django.db import models
from django.urls import reverse

class TimeStampedModel(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

class SEOFields(models.Model):
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.CharField(max_length=300, blank=True)
    canonical_url = models.URLField(blank=True)
    
    class Meta:
        abstract = True
# gg
# apps/solutions/models.py
class SolutionCategory(TimeStampedModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, help_text="FontAwesome icon class")
    display_order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return self.name

class Solution(TimeStampedModel, SEOFields):
    category = models.ForeignKey(SolutionCategory, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    subtitle = models.CharField(max_length=300)
    featured_image = models.ImageField(upload_to='solutions/')
    overview = models.TextField()
    challenge = models.TextField(help_text="Industry challenge")
    approach = models.TextField(help_text="Our approach")
    results = models.TextField(help_text="Expected results")
    case_study = models.FileField(upload_to='case_studies/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['display_order', 'title']
    
    def get_absolute_url(self):
        return reverse('solution_detail', kwargs={'slug': self.slug})

# apps/demo/models.py
class DemoBooking(TimeStampedModel):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    company = models.CharField(max_length=200)
    job_title = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)
    industry = models.CharField(max_length=100)
    interest_areas = models.ManyToManyField('users.Solution')
    message = models.TextField(blank=True)
    preferred_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    calendly_event_id = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.company}"



from django.db import models

class Company(models.Model):
    name = models.CharField(max_length=255, unique=True)
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)

    def __str__(self):
        return self.name

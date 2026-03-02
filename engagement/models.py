from django.db import models
from django.utils import timezone
from tinymce.models import HTMLField

class Article(models.Model):
    title = models.CharField(max_length=200)
    content = HTMLField()   # This will use TinyMCE editor
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
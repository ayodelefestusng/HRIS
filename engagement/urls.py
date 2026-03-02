from rest_framework.routers import DefaultRouter
from .views import SurveyViewSet, PollViewSet, PulseCheckViewSet,create_article
from django.urls import path
router = DefaultRouter()
router.register(r"surveys", SurveyViewSet)
router.register(r"polls", PollViewSet)
router.register(r"pulse-checks", PulseCheckViewSet)

app_name = "engagement"
urlpatterns = [
      path("articles/", create_article, name="articles"),

]
urlpatterns += router.urls

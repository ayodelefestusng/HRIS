from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets
from employees.models import Survey, SurveyQuestion, SurveyResponse, Poll, PollOption, PollVote, PulseCheck
from .serializers import (
    SurveySerializer,
    SurveyQuestionSerializer,
    SurveyResponseSerializer,
    PollSerializer,
    PollOptionSerializer,
    PollVoteSerializer,
    PulseCheckSerializer,
)

class SurveyViewSet(viewsets.ModelViewSet):
    queryset = Survey.objects.all()
    serializer_class = SurveySerializer

class PollViewSet(viewsets.ModelViewSet):
    queryset = Poll.objects.all()
    serializer_class = PollSerializer

class PulseCheckViewSet(viewsets.ModelViewSet):
    queryset = PulseCheck.objects.all()
    serializer_class = PulseCheckSerializer


from django.shortcuts import render, redirect
from .forms import ArticleForm

def create_article(request):
    if request.method == 'POST':
        form = ArticleForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('article_list')
    else:
        form = ArticleForm()
    return render(request, 'engagement/create_article.html', {'form': form})
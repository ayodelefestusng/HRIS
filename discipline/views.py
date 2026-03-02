from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets
from .models import Warning, Suspension, Investigation
from .serializers import WarningSerializer, SuspensionSerializer, InvestigationSerializer

class WarningViewSet(viewsets.ModelViewSet):
    queryset = Warning.objects.all()
    serializer_class = WarningSerializer

class SuspensionViewSet(viewsets.ModelViewSet):
    queryset = Suspension.objects.all()
    serializer_class = SuspensionSerializer

class InvestigationViewSet(viewsets.ModelViewSet):
    queryset = Investigation.objects.all()
    serializer_class = InvestigationSerializer
from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, permissions
from .models import Role, Permission, RolePermission, EmployeeRole
from .serializers import (
    RoleSerializer,
    PermissionSerializer,
    RolePermissionSerializer,
    EmployeeRoleSerializer,
)


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated]


class PermissionViewSet(viewsets.ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAuthenticated]


class RolePermissionViewSet(viewsets.ModelViewSet):
    queryset = RolePermission.objects.all()
    serializer_class = RolePermissionSerializer
    permission_classes = [permissions.IsAuthenticated]


class EmployeeRoleViewSet(viewsets.ModelViewSet):
    queryset = EmployeeRole.objects.all()
    serializer_class = EmployeeRoleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    
    
from rest_framework.views import APIView
from rest_framework.response import Response
from rbac.models import Role


class PermissionMatrixView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        data = []
        for role in Role.objects.all():
            perms = role.permissions.values_list("code", flat=True)
            data.append({
                "role": role.name,
                "permissions": list(perms),
            })
        return Response(data)
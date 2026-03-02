from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RoleViewSet,
    PermissionViewSet,
    RolePermissionViewSet,
    EmployeeRoleViewSet,PermissionMatrixView
)

router = DefaultRouter()
router.register("roles", RoleViewSet)
router.register("permissions", PermissionViewSet)
router.register("role-permissions", RolePermissionViewSet)
router.register("employee-roles", EmployeeRoleViewSet)

urlpatterns = [
    path("", include(router.urls)),
     path("permission-matrix/", PermissionMatrixView.as_view()),

]
# user/permissions.py
# pyrefly: ignore [missing-import]
from rest_framework import permissions


class IsSuperAdmin(permissions.BasePermission):
    """Allow access only to Super Admin users"""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and (
                request.user.role in ('super_admin', 'admin') or 
                request.user.is_superuser or 
                request.user.is_staff
            )
        )


class IsCompany(permissions.BasePermission):
    """Allow access only to Company users"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'company'


class IsApplicant(permissions.BasePermission):
    """Allow access only to Applicant users"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'applicant'


class IsOwnerOrAdmin(permissions.BasePermission):
    """Allow access to object owner or Super Admin"""
    def has_object_permission(self, request, view, obj):
        if request.user.is_super_admin():
            return True
        return obj == request.user
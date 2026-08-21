from rest_framework import permissions


class IsExperienceOwner(permissions.BasePermission):
    """Allows only the profile owner to manage their work experience"""
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        return obj.profile.user == request.user


class IsEducationOwner(permissions.BasePermission):
    """Allows only the profile owner to manage their education"""
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        return obj.profile.user == request.user

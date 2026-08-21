from rest_framework import permissions


class IsCompany(permissions.BasePermission):
    """Allows access to authenticated users."""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_active
        )


class IsVerifiedCompany(permissions.BasePermission):
    """Allows access to verified accounts."""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_verified and
            request.user.is_active and
            not request.user.is_suspended
        )


class IsJobOwner(permissions.BasePermission):
    """
    Object-level permission to allow only the company that created the job
    (or a Super Admin) to edit or delete it.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.role == 'super_admin':
            return True
        return obj.company == request.user

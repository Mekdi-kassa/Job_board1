from rest_framework import permissions


class IsNotificationRecipient(permissions.BasePermission):
    """Allows access only to the recipient of the notification"""
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        return obj.recipient == request.user

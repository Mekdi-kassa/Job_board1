from rest_framework import permissions


class IsReportReporter(permissions.BasePermission):
    """Allows access only to the reporter who submitted the report"""
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        return obj.reporter == request.user

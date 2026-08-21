from rest_framework import permissions


class IsApplicationOwner(permissions.BasePermission):
    """
    Object-level permission allowing only the applicant who submitted the application
    (or Super Admin) to access/withdraw it.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.role == 'super_admin':
            return True
        return obj.applicant == request.user


class IsApplicationJobOwner(permissions.BasePermission):
    """
    Object-level permission allowing only the company that posted the job
    (or Super Admin) to review candidates and update their status.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.role == 'super_admin':
            return True
        return obj.job.company == request.user

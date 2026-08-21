from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Notification
from .serializers import NotificationSerializer
from .permissions import IsNotificationRecipient
from jobs.views import StandardResultsSetPagination


class NotificationListView(generics.ListAPIView):
    """
    List user's in-app notifications.
    Supports filtering by ?is_read=false and pagination.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Notification.objects.filter(recipient=self.request.user)
        is_read_param = self.request.query_params.get('is_read')
        if is_read_param is not None:
            if is_read_param.lower() in ('false', '0'):
                queryset = queryset.filter(is_read=False)
            elif is_read_param.lower() in ('true', '1'):
                queryset = queryset.filter(is_read=True)
        return queryset


class NotificationUnreadCountView(APIView):
    """
    Get unread notifications count for header badge.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({
            'success': True,
            'unread_count': count
        }, status=status.HTTP_200_OK)


class NotificationMarkReadView(APIView):
    """
    Mark a single notification as read.
    """
    permission_classes = [permissions.IsAuthenticated, IsNotificationRecipient]

    def patch(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk)
        self.check_object_permissions(request, notification)

        notification.is_read = True
        notification.save(update_fields=['is_read'])

        return Response({
            'success': True,
            'message': 'Notification marked as read.',
            'data': NotificationSerializer(notification).data
        }, status=status.HTTP_200_OK)


class NotificationMarkAllReadView(APIView):
    """
    Mark all user's unread notifications as read.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        updated_count = Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({
            'success': True,
            'message': f'Marked {updated_count} notifications as read.',
            'updated_count': updated_count
        }, status=status.HTTP_200_OK)


class NotificationDeleteView(APIView):
    """
    Delete a notification.
    """
    permission_classes = [permissions.IsAuthenticated, IsNotificationRecipient]

    def delete(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk)
        self.check_object_permissions(request, notification)
        notification.delete()

        return Response({
            'success': True,
            'message': 'Notification deleted successfully.'
        }, status=status.HTTP_200_OK)

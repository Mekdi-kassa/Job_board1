from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """In-App Notification Serializer"""
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'notification_type_display',
            'title', 'message', 'action_url', 'is_read', 'email_sent',
            'sender_name', 'created_at'
        ]
        read_only_fields = ['id', 'notification_type', 'title', 'message', 'action_url', 'email_sent', 'created_at']

    def get_sender_name(self, obj):
        if obj.sender:
            return obj.sender.get_full_name() or obj.sender.username
        return "Job Board System"

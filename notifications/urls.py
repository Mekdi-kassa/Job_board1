from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # List notifications
    path('', views.NotificationListView.as_view(), name='notification-list'),

    # Unread badge count
    path('unread-count/', views.NotificationUnreadCountView.as_view(), name='unread-count'),

    # Mark all as read
    path('mark-all-read/', views.NotificationMarkAllReadView.as_view(), name='mark-all-read'),

    # Mark single notification as read
    path('<uuid:pk>/read/', views.NotificationMarkReadView.as_view(), name='mark-read'),

    # Delete single notification
    path('<uuid:pk>/', views.NotificationDeleteView.as_view(), name='delete-notification'),
]

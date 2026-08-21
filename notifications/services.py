import os
from django.conf import settings
from .models import Notification
from user.utils import _send_via_sendgrid_https, _send_via_resend_https
from django.core.mail import send_mail


def _dispatch_email(to_email, subject, plain_message, html_message):
    """Multi-provider email dispatcher with SendGrid HTTPS & Resend"""
    try:
        from_email = os.getenv('DEFAULT_FROM_EMAIL', 'mekdelawitkassa6@gmail.com')
        if not from_email or 'noreply' in from_email:
            from_email = 'mekdelawitkassa6@gmail.com'

        # 1. Resend API
        resend_key = os.getenv('RESEND_API_KEY')
        if resend_key:
            try:
                _send_via_resend_https(resend_key, from_email, to_email, subject, plain_message, html_message)
                return True
            except Exception as e:
                print(f"Resend error: {e}")

        # 2. SendGrid API
        sendgrid_key = os.getenv('SENDGRID_API_KEY')
        if sendgrid_key:
            try:
                _send_via_sendgrid_https(sendgrid_key, from_email, to_email, subject, plain_message, html_message)
                return True
            except Exception as e:
                print(f"SendGrid error: {e}")

        # 3. Django fallback
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=from_email,
            recipient_list=[to_email],
            html_message=html_message,
            fail_silently=True,
        )
        return True
    except Exception as e:
        print(f"Failed to dispatch notification email: {e}")
        return False


def create_and_send_notification(recipient, notification_type, title, message, action_url="", sender=None, send_email=True):
    """
    Create in-app notification record and optionally dispatch SendGrid email alert.
    """
    notification = Notification.objects.create(
        recipient=recipient,
        sender=sender,
        notification_type=notification_type,
        title=title,
        message=message,
        action_url=action_url,
        is_read=False
    )

    if send_email and recipient.email:
        html_message = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f8fafc; padding: 24px; margin: 0;">
    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.06);">
        <tr>
            <td style="background-color: #2563eb; padding: 28px 24px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 22px;">🔔 {title}</h1>
            </td>
        </tr>
        <tr>
            <td style="padding: 32px 24px;">
                <p style="color: #334155; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                    {message}
                </p>
                <div style="text-align: center; margin-top: 28px;">
                    <a href="https://job-board1-sghl.onrender.com{action_url}" style="background-color: #2563eb; color: #ffffff; padding: 12px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block;">
                        View in Dashboard →
                    </a>
                </div>
            </td>
        </tr>
        <tr>
            <td style="background-color: #f8fafc; padding: 16px; text-align: center; border-top: 1px solid #e2e8f0;">
                <p style="color: #94a3b8; font-size: 12px; margin: 0;">Job Board Notifications System</p>
            </td>
        </tr>
    </table>
</body>
</html>"""
        dispatched = _dispatch_email(recipient.email, f"🔔 {title}", message, html_message)
        if dispatched:
            notification.email_sent = True
            notification.save(update_fields=['email_sent'])

    return notification


def notify_application_status_update(application):
    """Notify applicant when employer updates hiring status"""
    applicant = application.applicant
    job = application.job
    company_name = job.company.get_full_name() or job.company.username
    status_display = application.get_status_display()

    title = f"Application Status: {status_display}"
    message = f"Your application for {job.title} at {company_name} has been updated to '{status_display}'."
    action_url = f"/api/applications/my-applications/{application.id}/"

    return create_and_send_notification(
        recipient=applicant,
        sender=job.company,
        notification_type=Notification.NotificationType.APPLICATION_STATUS_UPDATE,
        title=title,
        message=message,
        action_url=action_url,
        send_email=True
    )


def notify_new_candidate(application):
    """Notify company when a new candidate applies"""
    applicant = application.applicant
    job = application.job
    company = job.company

    title = f"New Candidate for {job.title}"
    message = f"{applicant.get_full_name()} ({applicant.email}) has applied for your job listing: {job.title}."
    action_url = f"/api/applications/job/{job.id}/"

    return create_and_send_notification(
        recipient=company,
        sender=applicant,
        notification_type=Notification.NotificationType.NEW_APPLICANT,
        title=title,
        message=message,
        action_url=action_url,
        send_email=True
    )

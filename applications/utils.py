import os
from django.conf import settings
from user.utils import _send_via_sendgrid_https, _send_via_resend_https
from django.core.mail import send_mail


def _dispatch_email(to_email, subject, plain_message, html_message):
    """Safe multi-provider email dispatcher"""
    try:
        from_email = os.getenv('DEFAULT_FROM_EMAIL', 'mekdelawitkassa6@gmail.com')
        if not from_email or 'noreply' in from_email:
            from_email = 'mekdelawitkassa6@gmail.com'

        # 1. Resend HTTPS API
        resend_key = os.getenv('RESEND_API_KEY')
        if resend_key:
            try:
                _send_via_resend_https(resend_key, from_email, to_email, subject, plain_message, html_message)
                return True
            except Exception as e:
                print(f"Resend notification failed: {e}")

        # 2. SendGrid HTTPS API
        sendgrid_key = os.getenv('SENDGRID_API_KEY')
        if sendgrid_key:
            try:
                _send_via_sendgrid_https(sendgrid_key, from_email, to_email, subject, plain_message, html_message)
                return True
            except Exception as e:
                print(f"SendGrid notification failed: {e}")

        # 3. Django fallback
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            html_message=html_message,
            fail_silently=True,
        )
        return True
    except Exception as e:
        print(f"Notification email failed to dispatch: {e}")
        return False


def send_application_submitted_email(application):
    """Send confirmation email to applicant"""
    applicant = application.applicant
    job = application.job
    company_name = job.company.get_full_name() or job.company.username or "Employer"

    subject = f"🎯 Application Received: {job.title} at {company_name}"
    
    html_message = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f8fafc; padding: 24px;">
    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.06);">
        <tr>
            <td style="background-color: #2563eb; padding: 28px 24px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px;">🎯 Application Submitted!</h1>
            </td>
        </tr>
        <tr>
            <td style="padding: 32px 24px;">
                <h2 style="color: #1e293b; margin: 0 0 12px 0;">Hello, {applicant.get_full_name()}!</h2>
                <p style="color: #475569; font-size: 15px; line-height: 1.6;">
                    Your application for <strong>{job.title}</strong> at <strong>{company_name}</strong> has been successfully submitted and delivered to the hiring team.
                </p>
                <div style="background-color: #f1f5f9; padding: 16px 20px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 4px 0; color: #334155;"><strong>Job:</strong> {job.title}</p>
                    <p style="margin: 4px 0; color: #334155;"><strong>Location:</strong> {job.location} ({job.get_workplace_type_display()})</p>
                    <p style="margin: 4px 0; color: #334155;"><strong>Current Status:</strong> <span style="background-color: #dbeafe; color: #1e40af; padding: 3px 8px; border-radius: 4px; font-weight: 600;">Pending Review</span></p>
                </div>
                <p style="color: #64748b; font-size: 14px;">You will receive an automated notification whenever the employer updates your application status.</p>
            </td>
        </tr>
    </table>
</body>
</html>"""

    plain_message = f"Hello {applicant.get_full_name()},\n\nYour application for {job.title} at {company_name} has been received.\n\nStatus: Pending Review\n\nJob Board Team"
    return _dispatch_email(applicant.email, subject, plain_message, html_message)


def send_company_new_applicant_email(application):
    """Notify company that a new candidate has applied"""
    applicant = application.applicant
    job = application.job
    company = job.company

    subject = f"📬 New Candidate Applied: {applicant.get_full_name()} for {job.title}"

    html_message = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f8fafc; padding: 24px;">
    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.06);">
        <tr>
            <td style="background-color: #0f172a; padding: 28px 24px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px;">📬 New Candidate Application</h1>
            </td>
        </tr>
        <tr>
            <td style="padding: 32px 24px;">
                <h2 style="color: #1e293b; margin: 0 0 12px 0;">New Applicant Alert</h2>
                <p style="color: #475569; font-size: 15px; line-height: 1.6;">
                    A candidate has just applied for your job listing: <strong>{job.title}</strong>.
                </p>
                <div style="background-color: #f8fafc; border-left: 4px solid #2563eb; padding: 16px; border-radius: 4px; margin: 20px 0;">
                    <p style="margin: 4px 0; color: #1e293b;"><strong>Candidate:</strong> {applicant.get_full_name()}</p>
                    <p style="margin: 4px 0; color: #1e293b;"><strong>Email:</strong> {applicant.email}</p>
                </div>
                <p style="color: #64748b; font-size: 14px;">Log in to your employer dashboard to view their resume and advance their status.</p>
            </td>
        </tr>
    </table>
</body>
</html>"""

    plain_message = f"New candidate {applicant.get_full_name()} ({applicant.email}) applied for {job.title}."
    return _dispatch_email(company.email, subject, plain_message, html_message)


def send_application_status_update_email(application):
    """Notify applicant when company changes their application status"""
    applicant = application.applicant
    job = application.job
    company_name = job.company.get_full_name() or "The Employer"
    status_display = application.get_status_display()

    subject = f"🎉 Status Update: {job.title} at {company_name}"

    html_message = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f8fafc; padding: 24px;">
    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.06);">
        <tr>
            <td style="background-color: #2563eb; padding: 28px 24px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px;">Application Status Update</h1>
            </td>
        </tr>
        <tr>
            <td style="padding: 32px 24px;">
                <h2 style="color: #1e293b; margin: 0 0 12px 0;">Hello, {applicant.get_full_name()}!</h2>
                <p style="color: #475569; font-size: 15px; line-height: 1.6;">
                    There is an update on your application for <strong>{job.title}</strong> at <strong>{company_name}</strong>.
                </p>
                <div style="background-color: #f1f5f9; padding: 16px 20px; border-radius: 8px; margin: 20px 0; text-align: center;">
                    <p style="margin: 0; color: #475569; font-size: 13px;">New Status</p>
                    <h3 style="margin: 6px 0 0 0; color: #2563eb; font-size: 20px;">{status_display}</h3>
                </div>
            </td>
        </tr>
    </table>
</body>
</html>"""

    plain_message = f"Hello {applicant.get_full_name()},\n\nYour application status for {job.title} at {company_name} has been updated to: {status_display}."
    return _dispatch_email(applicant.email, subject, plain_message, html_message)

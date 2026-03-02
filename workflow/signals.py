from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def send_workflow_notification(instance, approver):
    subject = f"Action Required: {instance.workflow.name} - {instance.approval_ref}"
    from_email = "notifications@dignityconcept.tech"
    to_email = approver.user.email

    # Prepare context for the email template
    context = {
        'instance': instance,
        'approver': approver,
        'initiator': instance.initiated_by,
        'base_url': "http://yourdomain.com", # Change to your actual domain
    }

    html_content = render_to_string('workflow/emails/action_required.html', context)
    text_content = strip_tags(html_content)

    email = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
    email.attach_alternative(html_content, "text/html")
    email.send()
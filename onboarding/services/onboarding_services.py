# from django.utils import timezone
# from ats.models import (
#     OnboardingPlan,
#     OnboardingTask,
#     OnboardingTaskTemplate,
# )
# from notifications.services.notification_sender import create_notification
# from notifications.services.notification_sender import create_notification

# def create_onboarding_plan(employee, template, start_date=None):
#     plan = OnboardingPlan.objects.create(
#         employee=employee,
#         template=template,
#         start_date=start_date or timezone.now().date(),
#     )

#     task_templates = template.task_templates.order_by("order")

#     for t in task_templates:
#         task = OnboardingTask.objects.create(
#             plan=plan,
#             title=t.title,
#             description=t.description,
#             order=t.order,
#         )

#         # ✅ Notify employee for each task
#         create_notification(
#             recipient=employee.user,
#             title="New Onboarding Task Assigned",
#             message=f"You have a new onboarding task: {task.title}",
#             target=task,
#             send_email=False,
#         )

#     # ✅ Welcome notification
#     create_notification(
#         recipient=employee.user,
#         title="Welcome to the Company!",
#         message="Your onboarding plan has been created.",
#         target=plan,
#         send_email=True,
#     )

#     return plan



# def complete_task(task: OnboardingTask):
#     task.status = "DONE"
#     task.completed_at = timezone.now()
#     task.save()

#     # Notify employee
#     create_notification(
#         recipient=task.plan.employee.user,
#         title="Onboarding Task Completed",
#         message=f"You completed: {task.title}",
#         target=task,
#         send_email=False,
#     )

#     # Check if all tasks done
#     if not task.plan.tasks.exclude(status="DONE").exists():
#         task.plan.completed_at = timezone.now()
#         task.plan.save()

#         create_notification(
#             recipient=task.plan.employee.user,
#             title="Onboarding Completed",
#             message="Congratulations! You have completed your onboarding.",
#             target=task.plan,
#             send_email=True,
#         )

#     return task
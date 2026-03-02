from django.core.management.base import BaseCommand
from django.db import transaction
from workflow.models import Workflow, WorkflowStage
from org.models import JobRole, OrgUnit, Tenant # Adjust import based on your org app

class Command(BaseCommand):
    help = "Seeds Manager-Based and Role-Based workflows for testing"

    def handle(self, *args, **options):
        # Assuming we are seeding for the first tenant for testing
        tenant = Tenant.objects.first() 
        if not tenant:
            self.stdout.write(self.style.ERROR("No Tenant found. Create a tenant first."))
            return

        with transaction.atomic():
            self.seed_leave_workflow(tenant)
            self.seed_memo_workflow(tenant)
            self.stdout.write(self.style.SUCCESS("Successfully seeded workflows."))

    def seed_leave_workflow(self, tenant):
        """Manager-Based: Follows Line Manager Chain"""
        wf, _ = Workflow.objects.update_or_create(
            tenant=tenant,
            code="leave-approval",
            defaults={
                "name": "Annual Leave Process",
                "hierarchy_type": "MANAGER_CHAIN",
                "description": "Standard leave request following the management hierarchy."
            }
        )

        # Stage 1: Immediate Manager
        WorkflowStage.objects.update_or_create(
            tenant=tenant,
            workflow=wf,
            sequence=1,
            defaults={
                "name": "Line Manager Approval",
                "required_role": JobRole.objects.get(role_type="HEAD"), # Ensure this role exists
                "approval_type": "ANY",
                "system_status": "PENDING_MANAGER"
            }
        )

        # Stage 2: Final HR (Role-Based Step in a Manager Workflow)
        WorkflowStage.objects.update_or_create(
            tenant=tenant,
            workflow=wf,
            sequence=2,
            defaults={
                "name": "HR Final Review",
                "required_role": JobRole.objects.get(role_type="HR_MANAGER"),
                "is_final_stage": True,
                "system_status": "leave_application" # Your requested final state
            }
        )

    def seed_memo_workflow(self, tenant):
        """Role-Based: Specifically targets the Compliance/HR role"""
        wf, _ = Workflow.objects.update_or_create(
            tenant=tenant,
            code="memo-ack",
            defaults={
                "name": "Policy Acknowledgement",
                "hierarchy_type": "ROLE_BASED",
                "description": "Requires sign-off from the Compliance Department."
            }
        )

        WorkflowStage.objects.update_or_create(
            tenant=tenant,
            workflow=wf,
            sequence=1,
            defaults={
                "name": "Compliance Review",
                "required_role": OrgUnit.objects.get(code="COMPLIANCE_OFFICER"),
                "is_final_stage": True,
                "approval_type": "ALL", # Test sequential/all logic
                "system_status": "PUBLISHED"
            }
        )
        
    def seed_hybrid_workflow(self, tenant):
        """
        Hybrid: Stage 1 follows Line Manager, 
        Stage 2 targets a specific Executive Role.
        """
        wf, _ = Workflow.objects.update_or_create(
            tenant=tenant,
            code="capex-approval",
            defaults={
                "name": "Capital Expenditure (CAPEX)",
                "hierarchy_type": "HYBRID",
                "description": "Requires Line Manager approval followed by Finance Director sign-off."
            }
        )

        # Stage 1: Personal Management Chain
        WorkflowStage.objects.update_or_create(
            tenant=tenant,
            workflow=wf,
            sequence=1,
            defaults={
                "name": "Manager Review",
                "required_role": JobRole.objects.get(code="MANAGER"),
                "approval_type": "ANY",
                "system_status": "MANAGER_REVIEW"
            }
        )

        # Stage 2: Organizational Governance (Specific Role)
        WorkflowStage.objects.update_or_create(
            tenant=tenant,
            workflow=wf,
            sequence=2,
            defaults={
                "name": "Finance Director Final Approval",
                "required_role": JobRole.objects.get(code="FINANCE_DIRECTOR"),
                "is_final_stage": True,
                "approval_type": "ANY",
                "system_status": "APPROVED_FOR_PAYMENT"
            }
        )
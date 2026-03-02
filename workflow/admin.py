from django.contrib import admin
from .models import Workflow, WorkflowStage, WorkflowInstance, WorkflowAction, WorkflowTransition,WorkApprover

admin.site.register(WorkApprover)   
# @admin.register(WorkflowStage)

class WorkflowStepInline(admin.TabularInline):
    model = WorkflowStage
    extra = 1
@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ("name",)
    inlines = [WorkflowStepInline]






@admin.register(WorkflowInstance)
class WorkflowInstanceAdmin(admin.ModelAdmin):

    list_display = ("id", "workflow", "object_id", "content_type", "target", "created_at", "current_stage")
    # inlines = [WorkflowStageInstanceInline]

    @admin.display(description="Target Object")
    def target_info(self, obj):
        return f"{obj.content_type} (ID: {obj.object_id})"

    @admin.display(description="Workflow Stages")
    def stages(self, obj): 
        return ", ".join([f"Stage {s.sequence}" for s in obj.workflow.stages.all()]) 
    readonly_fields = ("stages",)


admin.site.register(WorkflowTransition) 
@admin.register(WorkflowAction)
class WorkflowActionAdmin(admin.ModelAdmin):
    list_display = ("id", "instance", "step", "actor", "action", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("comment", "actor__first_name", "actor__last_name")
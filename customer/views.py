import json
import os
import logging
from django.http import JsonResponse
from django.views import View
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from .models import Tenant_AI, Prompt,Opportunity  # Assuming your models are in models.py

logger = logging.getLogger(__name__)
from .chat_bot import get_llm_instance
from .chat_bot import initialize_vector_store,process_message
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

@method_decorator(csrf_exempt, name='dispatch')
class OnboardTenantView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            logger.info("Onboard View Called")
            
            # --- Trigger Global LLM Check/Creation ---
            # get_or_create_global_llm() # Your existing utility
            get_llm_instance()
            logger.info("Get Instance View Called")
            requested_prompt_type = data.get("prompt_type", "standard")
            default_prompt_name = os.getenv("name", "standard")

            with transaction.atomic():
                # Fetch or create prompt record
                prompt_record = Prompt.objects.filter(name=requested_prompt_type).first()

                if not prompt_record and requested_prompt_type != default_prompt_name:
                    logger.info(f"Prompt '{requested_prompt_type}' fallback to '{default_prompt_name}'")
                    prompt_record = Prompt.objects.filter(name=default_prompt_name).first()

                if not prompt_record:
                    logger.info(f"Creating '{default_prompt_name}' from env vars.")
                    prompt_record = Prompt.objects.create(
                        name=default_prompt_name,
                        is_hum_agent_allow_prompt=os.getenv("is_hum_agent_allow_prompt"),
                        no_hum_agent_allow_prompt=os.getenv("no_hum_agent_allow_prompt"),
                        summary_prompt=os.getenv("summary_prompt")
                    )

                # Create Tenant
                new_tenant = Tenant_AI.objects.create(
                    tenant_id=data.get("tenant_id"),
                    tenant_name=data.get("tenant_name"),
                    prompt_template=prompt_record,
                    prompt_type=requested_prompt_type,
                    tenant_website=data.get("tenant_website"),
                    tenant_knowledge_base=data.get("tenant_knowledge_base"),
                    tenant_text=data.get("tenant_text"),
                    tenant_document=data.get("tenant_document"),
                    is_hum_agent_allow=data.get("is_hum_agent_allow"),
                    conf_level=data.get("conf_level"),
                    sentiment_threshold=data.get("sentiment_threshold"),
                    message_tone=data.get("message_tone"),
                    ticket_type=data.get("ticket_type"),
                    chatbot_greeting=data.get("chatbot_greeting")
                )

            # Trigger AI Indexing
            logger.info(f"Tenant {new_tenant.tenant_id} committed. Initializing vector store.")
            initialize_vector_store(new_tenant.tenant_id)
            
            return JsonResponse({"status": "success", "message": "Tenant onboarded successfully"}, status=201)

        except Exception as e:
            logger.error(f"Onboarding error: {e}")
            return JsonResponse({"error": str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class TenantDetailView(View):
    def get(self, request):
        tenant_id = request.GET.get('tenant_id')
        tenant = Tenant_AI.objects.filter(tenant_id=tenant_id).first()
        if not tenant:
            return JsonResponse({"error": "Tenant not found"}, status=404)
        
        return JsonResponse({
            "tenant_id": tenant.tenant_id,
            "tenant_name": tenant.tenant_name,
            "chatbot_greeting": tenant.chatbot_greeting,
            "tenant_text": tenant.tenant_text,
            "is_hum_agent_allow": tenant.is_hum_agent_allow,
            # ... add other fields as needed
        })

    def post(self, request): # Update Logic
        try:
            data = json.loads(request.body)
            tenant_id = data.get("tenant_id")
            tenant = Tenant_AI.objects.filter(tenant_id=tenant_id).first()
            
            if not tenant:
                return JsonResponse({"error": "Tenant not found"}, status=404)

            # Update fields dynamically
            for key, value in data.items():
                if key != "tenant_id" and hasattr(tenant, key):
                    setattr(tenant, key, value)
            
            tenant.save()
            initialize_vector_store(tenant_id)
            return JsonResponse({"status": "success", "message": "Tenant updated."})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class ChatView(View):
    async def post(self, request):
        try:
            message_content = request.POST.get("message_content")
            conversation_id = request.POST.get("conversation_id")
            tenant_id = request.POST.get("tenant_id")
            summarization_request = request.POST.get("summarization_request") == 'true'
            user_msg_attach = request.FILES.get("user_msg_attach")

            # get_or_create_global_llm()
            get_llm_instance()

            file_path = None
            if user_msg_attach:
                # Save using Django's storage system
                path = f"chat_attachments/{user_msg_attach.name}"
                file_path = default_storage.save(path, ContentFile(user_msg_attach.read()))
                # default_storage returns the final path (handles name collisions)

            # Call your async processing logic
            response = await process_message(
                message_content=message_content,
                conversation_id=conversation_id,
                tenant_id=tenant_id,
                file_path=file_path,
                summarization_request=summarization_request
            )
            return JsonResponse(response)

        except Exception as e:
            logger.error(f"Chat error: {str(e)}")
            return JsonResponse({"error": "Internal Server Error"}, status=500)


class CRMPipelineView(LoginRequiredMixin, TemplateView):
    template_name = "workflow/crm_pipeline.html"

    def post(self, request, *args, **kwargs):
        action = request.GET.get('action')
        if action == 'move':
            opp_id = request.GET.get('id')
            to_stage = request.GET.get('to')
            try:
                opp = Opportunity.objects.get(pk=opp_id, tenant=request.user.tenant)
                # Instead of immediate update, trigger workflow
                opp.trigger_stage_transition(to_stage, request.user)
            except Opportunity.DoesNotExist:
                pass
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = getattr(self.request.user, 'tenant', None)
        
        # Group opportunities by stage
        stages = [choice[0] for choice in Opportunity.SALES_STAGE_CHOICES]
        pipeline = {stage: [] for stage in stages}
        
        opportunities = Opportunity.objects.filter(tenant=tenant).select_related('account', 'owner')
        for opp in opportunities:
            if opp.stage in pipeline:
                pipeline[opp.stage].append(opp)
        
        context['pipeline'] = pipeline
        context['stage_choices'] = Opportunity.SALES_STAGE_CHOICES
        return context



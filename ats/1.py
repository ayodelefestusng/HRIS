# --- Interview Scheduling ---

class ScheduleInterviewView(LoginRequiredMixin, CreateView):
    model = Interview
    template_name = "ats/schedule_interview.html"
    fields = ["application", "scheduled_at", "interviewers"]
    success_lazy = reverse_lazy("ats:manage_candidate")

    def form_valid(self, form):
        form.instance.tenant = self.request.user.tenant
        form.instance.setup_by = self.request.user.employee
        log_with_context(logging.INFO, f"Scheduling interview for Application ID: {form.instance.application.pk}", self.request.user)
        return super().form_valid(form)

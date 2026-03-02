class ScheduleInterviewView(LoginRequiredMixin, CreateView):
    model = Interview
    form_class = InterviewForm
    template_name = "ats/schedule_interview.html"
    success_url = reverse_lazy("ats:manage_candidate")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.user.tenant
        return kwargs

    def form_valid(self, form):
        form.instance.tenant = self.request.user.tenant
        form.instance.setup_by = self.request.user.employee
        return super().form_valid(form)
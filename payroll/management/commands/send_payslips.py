from django.core.management.base import BaseCommand
from payroll.models import PayrollPeriod, EmployeePayslip
from payroll.views import PayrollService

class Command(BaseCommand):
    help = "Sends payslip emails for a specific period"

    def add_arguments(self, parser):
        parser.add_argument('--period', type=str, help="Name of the payroll period")

    def handle(self, *args, **options):
        period_name = options['period']
        period = PayrollPeriod.objects.get(name=period_name)
        
        payslips = EmployeePayslip.objects.filter(entry__period=period)
        service = PayrollService(period)
        
        self.stdout.write(f"Sending {payslips.count()} emails...")
        
        for ps in payslips:
            service.send_employee_payslip_email(ps)
            self.stdout.write(self.style.SUCCESS(f"Sent to {ps.entry.employee.email}"))
import random
from faker import Faker
from django.core.management.base import BaseCommand
from org.models import Tenant, Grade
from payroll.models import GradeAllowance, AllowanceType
from ats.models import Application, Interview, InterviewFeedback
from employees.models import Employee

import random
from django.contrib.auth.models import User
from employees.models import Employee   # adjust import to your app
from faker import Faker
import random
from django.db import transaction
from org.models import Tenant

fake = Faker()
from django.contrib.auth import get_user_model
User = get_user_model()

class Command(BaseCommand):
    help = "Seed Grades, Employees, Applications, and Interviews for Tenant 3Line"
    def handle(self, *args, **options):
            tenant = Tenant.objects.get(code="DMC")


       
            # Cleaned unique data from your list
            nigerian_data1 = [
                ("Adeola", "Ogunjobi", "F"), ("Chikezie", "Nwosu", "M"), ("Fatima", "Abubakar", "F"),
                ("Obinna", "Eze", "M"), ("Ifeoma", "Okpara", "F"), ("Tunde", "Adeniyi", "M"),
                ("Aisha", "Mohammed", "F"), ("Emeka", "Igbokwe", "M"), ("Nneoma", "Achebe", "F"),
                ("Kolawole", "Ogunsola", "M"), ("Halima", "Suleiman", "F"), ("Godwin", "Okonkwo", "M"),
                ("Chimere", "Okafor", "F"), ("Bello", "Yusuf", "M"), ("Ezinne", "Nwankwo", "F"),
                ("Adewale", "Ojo", "M"), ("Funmi", "Adebayo", "F"), ("Ikechukwu", "Onwuka", "M"),
                ("Oluwaseun", "Akinyemi", "F"), ("Mutiu", "Adewale", "M"), ("Precious", "Onyema", "F"),
                ("Kingsley", "Okeke", "M"), ("Rukayat", "Ibrahim", "F"), ("Joseph", "Okorie", "M"),
                ("Aderonke", "Osunlana", "F"), ("Olumide", "Fagbemi", "M"), ("Ndidi", "Onyia", "F"),
                ("Babatunde", "Ogundele", "M"), ("Samirah", "Aliyu", "F"), ("Uchenna", "Madu", "M"),
                ("Chinyere", "Adebayo", "F"), ("Victor", "Mustafa", "M"), ("Zainab", "Ude", "F"),
                ("Ahmed", "Muktar", "M"), ("Lydia", "Godwin", "F"), ("Michael", "Abba", "M"),
                ("Roseline", "Ogunleye", "F"), ("Solomon", "Chinda", "M"), ("Beatrice", "Okeke", "F"),
                ("Anthony", "Samson", "M"), ("Juliet", "Saka", "F"), ("Bashir", "Kolawole", "M"),
                ("Amina", "Okolo", "F"), ("Abubakar", "Okafor", "M"), ("Evelyn", "Njoku", "F"),
                ("Prince", "Malam", "M"), ("Bukola", "Udeh", "F"), ("Isaac", "Gambo", "M"),
                ("Rose", "Onu", "F"), ("Hamisu", "Oni", "M"), ("Aisha", "Adeyemi", "F"),
                ("Chukwudi", "Okafor", "M"), ("Fatima", "Nwosu", "F"), ("Obi", "Eze", "M"),
                ("Ifeoma", "Adebayo", "F"), ("Tunde", "Ogunsola", "M"), ("Aisha", "Suleiman", "F")
            ]


            nigerian_names_list = [
            ("Emeka", "Igbokwe", "M"),
            ("Nneoma", "Achebe", "F"),
            ("Kolawole", "Ogunsola", "M"),
            ("Halima", "Suleiman", "F"),
            ("Godwin", "Okonkwo", "M"),
            ("Chimere", "Okafor", "F"),
            ("Bello", "Yusuf", "M"),
            ("Ezinne", "Nwankwo", "F"),
            ("Adewale", "Ojo", "M"),
            ("Funmi", "Adebayo", "F"),
            ("Ikechukwu", "Onwuka", "M"),
            ("Oluwaseun", "Akinyemi", "F"),
            ("Mutiu", "Adewale", "M"),
            ("Precious", "Onyema", "F"),
            ("Kingsley", "Okeke", "M"),
            ("Rukayat", "Ibrahim", "F"),
            ("Joseph", "Okorie", "M"),
            ("Aderonke", "Osunlana", "F"),
            ("Olumide", "Fagbemi", "M"),
            ("Ndidi", "Onyia", "F"),
            ("Babatunde", "Ogundele", "M"),
            ("Samirah", "Aliyu", "F"),
            ("Uchenna", "Madu", "M"),
            ("Aisha", "Adeyemi", "F"),
            ("Chukwudi", "Okafor", "M")
        ]
            nigerian_data_raw = nigerian_data1 + nigerian_names_list
            
            targets = Employee.objects.filter(
            user__full_name__in=["Floating Talent", "Ade Ojo"]
)
            # 2. Prepare our "DNA" pools from your existing Nigerian data
            first_names_f = [d[0] for d in nigerian_data_raw if d[2] == "F"]
            first_names_m = [d[0] for d in nigerian_data_raw if d[2] == "M"]
            last_names = list(set([d[1] for d in nigerian_data_raw]))
            middle_names = ["Olu", "Chukwu", "Abiodun", "Buchi", "Aminu", "Eniola", "Kelechi"]
            # seen_emails = set(User.objects.values_list('email', flat=True))
            # Fetch ALL employees for this tenant
   
            # 3. Track existing emails to maintain uniqueness
            # We clear this if we are resetting the whole DB, otherwise keep current users
            seen_emails = set()
            
            employees = Employee.objects.filter(tenant=tenant).select_related('user')
            total_count = employees.count()
            
            self.stdout.write(self.style.SUCCESS(f"Starting update for {total_count} records..."))
            
            # # --- STEP 1: DE-DUPLICATE THE LIST ---
            # nigerian_data = []
            # seen_emails = set()

            for first, last, gender in nigerian_data_raw:
                email = f"{first.lower()}.{last.lower()}@dignityconcept.tech"
                if email not in seen_emails:
                    nigerian_data.append((first, last, gender, email))
                    seen_emails.add(email)
                        # Fetch all existing employees
            # # --- STEP 2: UPDATE RECORDS ---
            # employees = Employee.objects.all()
            
            # # Track how many we can actually update
            # total_to_update = min(len(nigerian_data), employees.count())
            # self.stdout.write(self.style.SUCCESS(f"Total unique names available: {len(nigerian_data)}"))
            # self.stdout.write(self.style.SUCCESS(f"Total records to be updated: {total_to_update}"))



            with transaction.atomic():
                for emp in targets:
                    # Determine gender based on existing employee record or random
                    gender = emp.gender if emp.gender in ["M", "F"] else random.choice(["M", "F"])
                    # Keep trying until we generate a unique name/email combo
                while True:
                    first = random.choice(first_names_m if gender == "M" else first_names_f)
                    middle = random.choice(middle_names)
                    last = random.choice(last_names)
                    
                    # Combine them: e.g., "Adeola Olu Ogunjobi"
                    full_name = f"{first} {middle} {last}"
                    email = f"{first.lower()}.{middle.lower()}.{last.lower()}@dignityconcept.tech"
                    
                    if email not in seen_emails:
                        seen_emails.add(email)
                        break
            
                # for i in range(total_to_update):
                #     emp = employees[i]
                #     first, last, gender, email = nigerian_data[i]
                    
                #     full_name = f"{first} {last}"
                #     email = f"{first.lower()}.{last.lower()}@dignityconcept.tech"

                    # 1. Update the linked User account
                if emp.user:
                    emp.user.full_name = full_name
                    emp.user.email = email
                    # emp.user.username = email # Optional: usually username matches email
                    emp.user.save()

                # 2. Update the Employee record using its PK
                emp.first_name = f"{first} {middle}" # Combining first + middle
                emp.last_name = last
                emp.gender = gender
                emp.employee_email = email
                emp.save()

                self.stdout.write(f"Updated Placeholder PK {emp.pk} -> {full_name}")

            self.stdout.write(self.style.SUCCESS(f"Finished updating {targets.count()} placeholder records."))
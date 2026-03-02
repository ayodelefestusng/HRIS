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
from django.db import transaction, IntegrityError

fake = Faker()
from django.contrib.auth import get_user_model
User = get_user_model()
from django.db import transaction, IntegrityError
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
                
                # 1. Your unique data pool
                nigerian_data_raw = nigerian_data1 + nigerian_names_list
                
                # 2. Extract DNA for random generation
                nigerian_data_raw = nigerian_data1 + nigerian_names_list
                first_names_f = list(set([d[0] for d in nigerian_data_raw if d[2] == "F"]))
                first_names_m = list(set([d[0] for d in nigerian_data_raw if d[2] == "M"]))
                last_names = list(set([d[1] for d in nigerian_data_raw]))
                middle_names = ["Olu", "Chukwu", "Abiodun", "Buchi", "Aminu", "Eniola", "Kelechi", "Tobi"]
                # 2. Get the Tenant
                tenant = Tenant.objects.get(code="DMC")

                # 3. Pre-fetch ALL existing emails in the whole DB to avoid IntegrityErrors
                seen_emails = set(User.objects.values_list('email', flat=True))
                seen_names = set(User.objects.values_list('full_name', flat=True))

                # 4. Fetch all employees for this tenant
                employees = Employee.objects.filter(tenant=tenant).select_related('user')

                self.stdout.write(f"Commencing force update for {employees.count()} records...")

             
                for i, emp in enumerate(employees):
                    # Determine base Identity
                    if i < len(nigerian_data_raw):
                        first, last, gender = nigerian_data_raw[i]
                        middle = ""
                    else:
                        gender = emp.gender if emp.gender in ["M", "F"] else random.choice(["M", "F"])
                        first = random.choice(first_names_m if gender == "M" else first_names_f)
                        middle = random.choice(middle_names)
                        last = random.choice(last_names)

                    # 3. Unique Loop for BOTH Name and Email
                    attempt = 0
                    while True:
                        suffix = f" {attempt}" if attempt > 0 else ""
                        email_suffix = f"{attempt}" if attempt > 0 else ""
                        
                        # Build Name
                        if middle:
                            full_name = f"{first} {middle} {last}{suffix}".strip()
                            email = f"{first.lower()}.{middle.lower()}.{last.lower()}{email_suffix}@dignityconcept.tech"
                        else:
                            full_name = f"{first} {last}{suffix}".strip()
                            email = f"{first.lower()}.{last.lower()}{email_suffix}@dignityconcept.tech"
                        
                        # Check uniqueness for BOTH fields
                        if email not in seen_emails and full_name not in seen_names:
                            seen_emails.add(email)
                            seen_names.add(full_name)
                            break
                        attempt += 1

                    # 4. Atomic Update
                    try:
                        with transaction.atomic():
                            if emp.user:
                                u = emp.user
                                u.full_name = full_name
                                u.email = email
                                u.username = email
                                u.save()

                            emp.first_name = first if not middle else f"{first} {middle}"
                            emp.last_name = last
                            emp.gender = gender
                            emp.employee_email = email
                            emp.save()
                            
                            self.stdout.write(self.style.SUCCESS(f"Record {emp.pk} -> {full_name}"))
                            
                    except IntegrityError as e:
                        self.stdout.write(self.style.ERROR(f"Failed PK {emp.pk}: {e}"))

                self.stdout.write(self.style.SUCCESS("Full update complete. No more 'Ade Ojo' should remain."))
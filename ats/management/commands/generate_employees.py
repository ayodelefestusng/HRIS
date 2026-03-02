import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from employees.models import Employee, Gender

User = get_user_model()

NIGERIAN_STATES = [
    "Lagos", "Abuja", "Kano", "Kaduna", "Rivers", "Oyo", "Ogun", "Delta",
    "Edo", "Enugu", "Anambra", "Imo", "Abia", "Katsina", "Bauchi", "Plateau",
    "Benue", "Kogi", "Nasarawa", "Sokoto", "Zamfara", "Kebbi", "Niger",
    "Taraba", "Adamawa", "Gombe", "Yobe", "Borno", "Cross River", "Akwa Ibom"
]

FIRST_NAMES_MALE = ["Emeka", "Tunde", "Ibrahim", "Chinedu", "Kunle", "Sani", "Femi", "Yusuf"]
FIRST_NAMES_FEMALE = ["Aisha", "Chioma", "Bisi", "Zainab", "Ada", "Halima", "Kemi", "Fatima"]
LAST_NAMES = ["Okafor", "Balogun", "Abdullahi", "Olawale", "Mohammed", "Eze", "Ogunleye", "Danladi"]


class Command(BaseCommand):
    help = "Generate 50 random employee records"

    def handle(self, *args, **kwargs):
        for i in range(150):
            gender = random.choice([Gender.MALE, Gender.FEMALE])

            if gender == Gender.MALE:
                first_name = random.choice(FIRST_NAMES_MALE)
            else:
                first_name = random.choice(FIRST_NAMES_FEMALE)

            last_name = random.choice(LAST_NAMES)

            # Generate age between 18 and 60
            age = random.randint(19, 60)
            today = date.today()

            birth_year = today.year - age
            birth_month = random.randint(1, 12)
            birth_day = random.randint(1, 28)  # safe for all months

            dob = date(birth_year, birth_month, birth_day)


            state = random.choice(NIGERIAN_STATES)

            employee_id = f"EMP{random.randint(10000, 99999)}"

            email = f"{first_name.lower()}.{last_name.lower()}{random.randint(1,99)}@example.com"
            email2 = f"{first_name.lower()}.{last_name.lower()}{random.randint(1,99)}@dmc.com"
            national_id_number =random.randint(1,99007)
            # Create linked user
            user = User.objects.create_user(
                # username=email,
                email=email,
                password="password123"
            )

            Employee.objects.create(
                user=user,
                employee_id=employee_id,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=dob,
                gender=gender,
                personal_email=email,
                employee_email=email2,
                phone_number=f"+23480{random.randint(10000000, 99999999)}",
                state=state,
                country="Nigeria",
                national_id_number=national_id_number,
            )

        self.stdout.write(self.style.SUCCESS("Successfully generated 50 employees"))
from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker
import random

from customer.models import (
    Customer,
    Transaction,
    BranchPerformance,
    Opportunity,
    Lead,
    Contact,
    Account,
)
from org.models import Location


class Command(BaseCommand):
    help = "Populate customer app models with sample data for testing/demos."

    def handle(self, *args, **options):
        fake = Faker()

        # wipe out existing data so the command is idempotent
        self.stdout.write(self.style.NOTICE("Clearing existing customer data..."))
        Transaction.objects.all().delete()
        BranchPerformance.objects.all().delete()
        Opportunity.objects.all().delete()
        Lead.objects.all().delete()
        Contact.objects.all().delete()
        Account.objects.all().delete()
        Customer.objects.all().delete()

        # --- ensure there are some branches available ----
        # Branch field should reference Location objects whose name ends with "Branch".
        # delete any existing branch locations so we start fresh
        # Location.objects.filter(name__iendswith="Branch").delete()
        # Location requires a town (and location_id) so we create a generic hierarchy.
        from org.models import Country, State, Town

        country, _ = Country.objects.get_or_create(name="Nigeria")
        state, _ = State.objects.get_or_create(name="Generic State", country=country)
        town, _ = Town.objects.get_or_create(name="Generic Town", state=state)

        sample_branch_names = [
            "Main Branch",
            "North Branch",
            "South Branch",
            "East Branch",
            "West Branch",
        ]
        branches = []
        for idx, name in enumerate(sample_branch_names, start=1):
            loc, created = Location.objects.get_or_create(
                name=name,
                defaults={
                    "location_id": f"BR{idx:03d}",
                    "town": town,
                },
            )
            branches.append(loc)

        # also include any existing branches matching the filter in case they were added manually
        extra = list(Location.objects.filter(name__iendswith="Branch").exclude(id__in=[b.id for b in branches]))
        branches.extend(extra)

        self.stdout.write(self.style.NOTICE(f"Using {len(branches)} branch locations (name ends with 'Branch')."))

        # ---- customers ----
        customers = []
        for i in range(120):
            customer_id = f"CUST{i+1:04d}"
            first = fake.first_name()
            last = fake.last_name()
            email = f"{first.lower()}.{last.lower()}{i}@example.com"
            phone = "0" + fake.random_element(elements=(
                "809", "817", "818", "909", "908",
            )) + f"{fake.random_number(digits=7, fix_len=True):07d}"
            account_num = f"{fake.random_number(digits=10, fix_len=True):010d}"
            gender = random.choice(["male", "female"])
            dob = fake.date_of_birth(minimum_age=18, maximum_age=70)

            obj, created = Customer.objects.get_or_create(
                customer_id=customer_id,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "email": email,
                    "phone_number": phone,
                    "account_number": account_num,
                    "gender": gender,
                    "nationality": "Nigeria",
                    "occupation": fake.job(),
                    "date_of_birth": dob,
                    "branch": random.choice(branches),
                },
            )
            customers.append(obj)
        self.stdout.write(self.style.SUCCESS(f"Created {len(customers)} customers."))

        # ---- accounts and contacts ----
        accounts = []
        for i in range(50):
            acct, _ = Account.objects.get_or_create(name=fake.company() + f" {i}")
            accounts.append(acct)

        contacts = []
        for i in range(134):
            first = fake.first_name()
            last = fake.last_name()
            # keep email short to avoid exceeding any varchar limits
            email = f"contact{i}@example.com"
            acct = random.choice(accounts)
            obj, created = Contact.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    # truncate phone to fit max_length of 20
                    "phone": fake.phone_number()[:20],
                    "account": acct,
                },
            )
            contacts.append(obj)
        self.stdout.write(self.style.SUCCESS(f"Created/collected {len(contacts)} contacts."))

        # ---- leads ----
        leads = []
        status_choices = [c[0] for c in Lead.LEAD_STATUS_CHOICES]
        source_choices = [c[0] for c in Lead.LEAD_SOURCE_CHOICES]
        for i in range(120):
            first = fake.first_name()
            last = fake.last_name()
            # keep lead email short to avoid varchar(20 limit
            email = f"lead{i}@example.com"
            obj, created = Lead.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "phone": fake.phone_number(),
                    "company": fake.company(),
                    "status": random.choice(status_choices),
                    "source": random.choice(source_choices),
                },
            )
            leads.append(obj)
        self.stdout.write(self.style.SUCCESS(f"Created {len(leads)} leads."))

        # ---- opportunities ----
        for i in range(23):
            acct = random.choice(accounts)
            contact = random.choice(contacts) if contacts else None
            Opportunity.objects.get_or_create(
                name=f"Sample Opportunity {i+1}",
                defaults={
                    "account": acct,
                    "contact": contact,
                    "amount": round(random.uniform(1000, 100000), 2),
                    "close_date": fake.date_between(start_date="-1y", end_date="+1y"),
                    "stage": random.choice([c[0] for c in Opportunity.SALES_STAGE_CHOICES]),
                    "probability": random.choice([c[0] for c in Opportunity.PROBABILITY_CHOICES]),
                },
            )
        self.stdout.write(self.style.SUCCESS("Created 23 opportunities."))

        # ---- transactions ----
        # produce 20,000 records evenly distributed across each month from
        # Jan 2023 through Mar 2026 (inclusive)
        start = timezone.datetime(2023, 1, 1, tzinfo=timezone.UTC)
        end = timezone.datetime(2026, 3, 4, tzinfo=timezone.UTC)
        # build list of (year, month) tuples
        months = []
        cur = start.replace(day=1)
        while cur <= end:
            months.append((cur.year, cur.month))
            # advance one month
            if cur.month == 12:
                cur = cur.replace(year=cur.year + 1, month=1)
            else:
                cur = cur.replace(month=cur.month + 1)
        total_months = len(months)
        # assign each month a random weight, convert to counts summing to 20k
        weights = [random.random() for _ in range(total_months)]
        total_weight = sum(weights)
        counts = [int(w / total_weight * 20000) for w in weights]
        # adjust for rounding
        diff = 20000 - sum(counts)
        for i in range(diff):
            counts[i % total_months] += 1

        txn_count = 0
        for (yr, mth), count in zip(months, counts):
            # compute month boundaries
            month_start = timezone.datetime(yr, mth, 1, tzinfo=timezone.UTC)
            if mth == 12:
                next_month = timezone.datetime(yr + 1, 1, 1, tzinfo=timezone.UTC)
            else:
                next_month = timezone.datetime(yr, mth + 1, 1, tzinfo=timezone.UTC)
            for j in range(count):
                cust = random.choice(customers)
                txn_type = random.choice([c[0] for c in Transaction.TRANSACTION_TYPES])
                # amount rules
                if txn_type == "balance_enquiry":
                    amount = 0
                else:
                    amount = round(random.uniform(1, 100000), 2)
                # service charge rules
                if txn_type in ("balance_enquiry", "airtime", "deposit"):
                    svc = 0
                else:
                    svc = 100
                channel = random.choice([c[0] for c in Transaction.TRANSACTION_CHANNELS])
                # random timestamp within the month
                timestamp = fake.date_time_between(start_date=month_start, end_date=next_month, tzinfo=timezone.UTC)
                # create record
                txn_count += 1
                Transaction.objects.create(
                    transaction_id=f"TXN{txn_count:08d}",
                    customer=cust,
                    transaction_type=txn_type,
                    amount=amount,
                    service_charge=svc,
                    transaction_channel=channel,
                    timestamp=timestamp,
                )
        self.stdout.write(self.style.SUCCESS(f"Created {txn_count} transactions."))

        # ---- branch performance ----
        for i in range(50):
            BranchPerformance.objects.create(
                branch=random.choice(branches),
                total_customers=random.randint(0, 200),
                total_transactions=random.randint(0, 1000),
                revenue_generated=round(random.uniform(0, 100000), 2),
            )
        self.stdout.write(self.style.SUCCESS("Created 50 branch performance records."))

        self.stdout.write(self.style.SUCCESS("Sample dataset generation finished."))

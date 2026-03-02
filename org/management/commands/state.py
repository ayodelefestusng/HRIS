from django.core.management.base import BaseCommand
from org.models import State, Town  # replace 'myapp' with your actual app name

class Command(BaseCommand):
    help = "List five towns in each state"

    def handle(self, *args, **options):
        states = [
            "Edo", "Delta", "Imo", "Anambra", "Oyo", "Ondo",
            "Kaduna", "Sokoto", "Nasarawa", "Gombe", "Borno", "Kano",
            "Benue", "Abuja", "Lagos"
        ]

        result = {}
        for state_name in states:
            try:
                state = State.objects.get(name__iexact=state_name)
                towns = Town.objects.filter(state=state).order_by('name')[:5]
                result[state.name] = [town.name for town in towns]
            except State.DoesNotExist:
                result[state_name] = []

        # Print nicely
        for state, towns in result.items():
            self.stdout.write(f"{state}: {', '.join(towns)}")
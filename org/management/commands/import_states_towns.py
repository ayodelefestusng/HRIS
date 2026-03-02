import json
from django.core.management.base import BaseCommand
from org.models import State, Town, Country

class Command(BaseCommand):
    help = "Import states and towns from Buyrite export and attach to Nigeria"

    def add_arguments(self, parser):
        parser.add_argument("json_file", type=str, help="Path to states_towns.json")

    def handle(self, *args, **options):
        json_file = options.get("json_file")
        if not json_file:
            self.stdout.write(self.style.ERROR("No json_file argument provided"))
            return

        try:
           with open(json_file, "r", encoding="utf-16") as f:
                data = json.load(f)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to parse JSON: {e}"))
            return

        if not isinstance(data, list):
            self.stdout.write(self.style.ERROR("JSON root should be a list of fixtures"))
            return

        nigeria, _ = Country.objects.get_or_create(name="Nigeria")
        state_map = {}

        # First pass: states
        for entry in data:
            if entry.get("model", "").endswith("state"):
                state_name = entry["fields"].get("name")
                if state_name:
                    state, _ = State.objects.get_or_create(name=state_name, country=nigeria)
                    state_map[entry["pk"]] = state

        # Second pass: towns
        for entry in data:
            if entry.get("model", "").endswith("town"):
                town_name = entry["fields"].get("name")
                old_state_id = entry["fields"].get("state")
                state = state_map.get(old_state_id)
                if town_name and state:
                    Town.objects.get_or_create(name=town_name, state=state)

        self.stdout.write(self.style.SUCCESS("States and towns imported successfully"))
        print("Loaded entries:", len(data))
        if data:
            print("First entry:", data[0])
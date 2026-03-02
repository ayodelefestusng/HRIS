import json
from org.models import State, Town

def get_towns_by_state():
    states = [
        "Edo", "Delta", "Imo", "Anambra", "Oyo", "Ondo",
        "Kaduna", "Sokoto", "Nasarawa", "Gombe", "Borno", "Kano",
        "Benue", "FCT", "Lagos","Rivers",
    ]

    result = {}

    for state_name in states:
        try:
            state = State.objects.get(name__iexact=state_name)
            towns = Town.objects.filter(state=state).order_by('name')[:5]
            result[state.name] = [town.name for town in towns]
        except State.DoesNotExist:
            result[state_name] = []

    # Return as dictionary
    return result

# If you want JSON output:
def get_towns_by_state_json():
    return json.dumps(get_towns_by_state(), indent=4)
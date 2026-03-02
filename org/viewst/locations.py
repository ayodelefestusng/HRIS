from rest_framework import viewsets
from org.models import Country, State, Town, Location
from org.serializers import CountrySerializer, StateSerializer, TownSerializer, LocationSerializer


class CountryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing countries.

    Provides CRUD operations:
    - GET /countries/ → List all countries
    - POST /countries/ → Create a new country
    - GET /countries/{id}/ → Retrieve a specific country
    - PUT/PATCH /countries/{id}/ → Update a country
    - DELETE /countries/{id}/ → Delete a country
    """
    queryset = Country.objects.all()
    serializer_class = CountrySerializer


class StateViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing states within countries.

    Provides CRUD operations:
    - GET /states/ → List all states
    - POST /states/ → Create a new state (requires country_id)
    - GET /states/{id}/ → Retrieve a specific state
    - PUT/PATCH /states/{id}/ → Update a state
    - DELETE /states/{id}/ → Delete a state
    """
    queryset = State.objects.select_related("country").all()
    serializer_class = StateSerializer


class TownViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing towns within states.

    Provides CRUD operations:
    - GET /towns/ → List all towns
    - POST /towns/ → Create a new town (requires state_id)
    - GET /towns/{id}/ → Retrieve a specific town
    - PUT/PATCH /towns/{id}/ → Update a town
    - DELETE /towns/{id}/ → Delete a town
    """
    queryset = Town.objects.select_related("state", "state__country").all()
    serializer_class = TownSerializer


class LocationViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing organizational locations.

    Provides CRUD operations:
    - GET /locations/ → List all locations
    - POST /locations/ → Create a new location (requires town_id, optional head employee)
    - GET /locations/{id}/ → Retrieve a specific location
    - PUT/PATCH /locations/{id}/ → Update a location
    - DELETE /locations/{id}/ → Delete a location

    Each location is linked to a town → state → country hierarchy,
    and may optionally have a head employee assigned.
    """
    queryset = Location.objects.select_related(
        "town", "town__state", "town__state__country", "head"
    ).all()
    serializer_class = LocationSerializer
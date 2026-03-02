from rest_framework import serializers
from .models import OrgUnit, OrgUnitVersion, OrgSnapshot, OrgWorkflowRoute


from rest_framework import serializers
from .models import OrgUnit
from .models import Location


class OrgUnitVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgUnitVersion
        fields = "__all__"


class OrgSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgSnapshot
        fields = "__all__"


class OrgWorkflowRouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgWorkflowRoute
        fields = "__all__"
        
        
from rest_framework import serializers
from .models import Country, State, Town, Location

class CountrySerializer(serializers.ModelSerializer):
    """Serializer for Country model."""
    class Meta:
        model = Country
        fields = "__all__"


class StateSerializer(serializers.ModelSerializer):
    """Serializer for State model, includes nested country details."""
    country = CountrySerializer(read_only=True)
    country_id = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(), source="country", write_only=True
    )

    class Meta:
        model = State
        fields = ["id", "name", "country", "country_id"]


class TownSerializer(serializers.ModelSerializer):
    """Serializer for Town model, includes nested state details."""
    state = StateSerializer(read_only=True)
    state_id = serializers.PrimaryKeyRelatedField(
        queryset=State.objects.all(), source="state", write_only=True
    )

    class Meta:
        model = Town
        fields = ["id", "name", "state", "state_id"]


class LocationSerializer(serializers.ModelSerializer):
    """Serializer for Location model, includes nested town/state/country details."""
    town = TownSerializer(read_only=True)
    town_id = serializers.PrimaryKeyRelatedField(
        queryset=Town.objects.all(), source="town", write_only=True
    )

    class Meta:
        model = Location
        fields = ["id", "location_id", "name", "address", "town", "town_id", "head"]
        
        
from rest_framework import serializers
from org.models import JobRole, RoleOfficerInCharge, RoleCompetencyRequirement, RoleSkillRequirement


class OrgUnitSerializer(serializers.ModelSerializer):
    """
    Serializer for OrgUnit model.
    - Includes recursive children.
    - Includes nested Location details for read.
    - Accepts location_id for write.
    """
    children = serializers.SerializerMethodField()
    location = LocationSerializer(read_only=True)
    location_id = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(),
        source="location",
        write_only=True
    )

    class Meta:
        model = OrgUnit
        fields = [
            "id", "name", "code", "parent", "path", "depth",
            "cost_center", "budget", "headcount_limit",
            "sort_order", "children",
            "location", "location_id"
        ]

    def get_children(self, obj):
        qs = obj.children.order_by("sort_order")
        return OrgUnitSerializer(qs, many=True).data



from rest_framework import serializers



class OrgUnitFlatSerializer(serializers.ModelSerializer):
    """
    Flat serializer for OrgUnit.
    - Does not include recursive children.
    - Includes nested Location details for read.
    - Accepts location_id for write.
    """
    location = LocationSerializer(read_only=True)
    location_id = serializers.PrimaryKeyRelatedField(
        queryset=LocationSerializer.Meta.model.objects.all(),
        source="location",
        write_only=True
    )

    class Meta:
        model = OrgUnit
        fields = [
            "id", "name", "code", "parent", "path", "depth",
            "cost_center", "budget", "headcount_limit",
            "sort_order", "created_at", "updated_at",
            "location", "location_id"
        ]

class OrgUnitRoleSerializer(serializers.ModelSerializer):
    """Serializer for OrgUnitRole model (Head, Deputy, Member)."""
    class Meta:
        model = JobRole
        fields = "__all__"

class OrgUnitSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = OrgUnit
        fields = [
            "id", "name", "code", "parent", "path", "depth",
            "cost_center", "budget", "headcount_limit",
            "sort_order", "children", "location"
        ]

    def get_children(self, obj):
        qs = obj.children.order_by("sort_order")
        return OrgUnitSerializer(qs, many=True).data
    
    
class RoleOfficerInChargeSerializer(serializers.ModelSerializer):
    """Serializer for RoleOfficerInCharge model."""
    class Meta:
        model = RoleOfficerInCharge
        fields = "__all__"


class RoleCompetencyRequirementSerializer(serializers.ModelSerializer):
    """Serializer for competency requirements linked to a role."""
    class Meta:
        model = RoleCompetencyRequirement
        fields = "__all__"


class RoleSkillRequirementSerializer(serializers.ModelSerializer):
    """Serializer for skill requirements linked to a role."""
    class Meta:
        model = RoleSkillRequirement
        fields = "__all__"
from itsdangerous import Serializer
from rest_framework import serializers
from api.models import *
from django.core.validators import validate_comma_separated_integer_list



#---------- Organizations ------------------

#serializer for returned data when retrieving or creating a single Organizations
class OrganizationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Organization
        fields = ('id', 'name', 'employees', 'industry', 'country', 'city', 'field',
                'timezone', 'subscription_plan',)
        read_only_fields = ('id','subscription_plan','date_created')

    def create(self, validated_data):
        service = self.context['service']
        instance = service.create(validated_data)
        return instance

#serializer for returned data when retrieving or creating a single Organizations
class OrganizationUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    employees = serializers.BooleanField(required=False)
    country = serializers.CharField(required=False)
    city = serializers.CharField(required=False)
    industry = serializers.CharField(required=False)
    timezone = serializers.CharField(required=False)

    def update(self, organization_id, validated_data):
        service = self.context['service']
        instance = service.update(organization_id, validated_data)
        return instance

   
#serializer for returned data when retrieving or creating a single user
class UserSerializer(serializers.ModelSerializer):
    memberships = serializers.ListField(child=OrganizationMembershipSerializer())

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'timezone', 'email', 'is_active', 'date_joined')
        read_only_fields = ('id', 'is_active', 'date_joined')
    

    def update(self, user_id, validated_data):
        service = self.context['service']
        instance = service.update(user_id, validated_data)
        return instance
 

#---------------  OrganizationMember ------------ 

class OrganizationMembershipSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrganizationMembership
        fields = ('id', 'organization_id', 'role', 'is_key_contact', 'date_created')
        read_only_fields = ('id', 'date_created')
    

    def update(self, membership_id, validated_data):
        service = self.context['service']
        instance = service.update(membership_id, validated_data)
        return instance
    
  
#--------------- AuthSerializer ----------------------
class AuthSerializer(serializers.Serializer):
    client_id = serializers.CharField()
    client_secret = serializers.CharField()

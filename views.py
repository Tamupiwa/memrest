from django.shortcuts import render
import os
from rest_framework.exceptions import *
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_access_policy import AccessViewSetMixin
from api.permissions.roles import *
from api import serializers
from rest_framework.response import Response


#overides model viewset to include getting scoped queryset and permissioned orgs 
class ModelViewSet_(viewsets.ModelViewSet):
    
    #returns existing resources users has permission
    def get_queryset(self, request, action, organization_id=None):
        return self.access_policy().scope_queryset(
            request=request,
            action=action,
            role_scoped=True,
            organization_id=organization_id)

    #used to get organizations user has permmission to create new resources
    def permissed_orgs(self, request, action, organization_id=None):
        return self.access_policy().get_permissioned_organizations(
            request=request, 
            action=action,
            role_scoped=True,
            organization_id=organization_id)
      


#endpoint for managing organizations
class OrganizationsViewSet(AccessViewSetMixin, ModelViewSet_):
    access_policy = OrganizationsAccessPolicy

    #lists all users organizations 
    def list(self, request):
        queryset = self.get_queryset(request, 'list')
        service = services.organizations.OrganizationService(self.request, queryset)
        organizations = service.all()
        data = serializers.OrganizationSerializer(organizations, many=True).data
        return Response(data, status=200, content_type='application/json')

    #creates a new organization
    def create(self, request):
        queryset = self.get_queryset(request, 'create')
        permissed_orgs = self.permissed_orgs(request, 'create')
        service = services.organizations.OrganizationService(self.request, queryset, permissed_orgs)
        serializer = serializers.OrganizationSerializer(data=request.data, context={"service": service})
        serializer.is_valid(raise_exception=True)
        org = serializer.save()
        data = serializers.OrganizationSerializer(org).data
        return Response(data, status=200, content_type='application/json')

    #retrieves an organization
    def retrieve(self, request, pk):
        queryset = self.get_queryset(request, 'retrieve')
        service = services.organizations.OrganizationService(self.request, queryset)
        organization = service.get_or_raise(pk)
        data = serializers.OrganizationSerializer(organization).data
        return Response(data, status=200, content_type='application/json')
    
    #updates an existing organization
    def update(self, request, pk):
        queryset = self.get_queryset(request, 'update')
        service = services.organizations.OrganizationService(self.request, queryset)
        serializer = serializers.OrganizationUpdateSerializer(data=request.data, context={"service": service})
        serializer.is_valid(raise_exception=True)
        serializer.update(pk, serializer.validated_data)
        return Response(status=204, content_type='application/json')

    #archives an organization
    def destroy(self, request, pk):
        queryset = self.get_queryset(request, 'delete')
        service = services.organizations.OrganizationService(self.request, queryset)
        service.delete(pk)
        return Response(status=204, content_type='application/json')

    #*** 
    #returns dashboard data for an organization
    def dasbboard_data(self, request):        
        queryset = self.get_queryset(request, 'dashboard_data')
        service = services.organizations.Organizations(self.request, queryset)
        serializer = serializers.RequestDashboardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = service.get_dashboard_data(pk)
        data = serializers.DashboardDataSerializer(data).data
        return Response(data, status=200, content_type='application/json')

    #returns dashboard data for an organization
    def dummy_dasbboard_data(self, request):
        queryset = self.get_queryset(request, 'dummy_dashboard_data')
        service = services.organizations.Organizations(self.request, queryset)
        serializer.is_valid(raise_exception=True)
        data = service.get_dummy_dashboard_data()
        data = serializers.DashboardDataSerializer(data).data
        return Response(data, status=200, content_type='application/json')
    
    def Reassign_facility_manager(self):
        pass

#endpoint for managing organization memberships (relationships between an organization and its users. organization/<id>/users/<id )
class OrganizationMembershipViewSet(AccessViewSetMixin, ModelViewSet_):
    access_policy = OrganizationMembershipsAccessPolicy
            
    #lists all users in the organization and their organizational meta data
    def list(self, request):
        #get all organization users
        serializer = serializers.GenericListSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        organization_id = serializer.validated_data.get('organization_id')
        user_id = serializer.validated_data.get('user_id')
        queryset = self.get_queryset(request, 'list', organization_id)
        service = services.organization_users.OrganizationsUsers(self.request, queryset)
        organization_users = service.all(organization_id, user_id)
        data = OrganizationsUsersSerializer(organization_users, many=True)
        return Response(data, status=200, content_type='application/json')

    #retrieves a organization
    def retrieve(self, request, pk):
        queryset = self.get_queryset(request, 'retrieve')
        service = services.organization_users.OrganizationsUsers(self.request, queryset)
        #gets organization and validates user belongs to organization
        organization_user = service.get_or_raise(pk)
        data = OrganizationMembershipSerializer(organization_user).data
        return Response(data, status=200, content_type='application/json')
    
    #updates an existing organization
    def update(self, request, pk):
        queryset = self.get_queryset(request, 'update')
        service = services.organization_users.OrganizationsUsers(self.request, queryset)
        serializer = serializers.OrganizationMemberSerializer(data=request.data, contex={'service': service})
        serializer.is_valid(raise_exception=True)
        serializer.update()
        return Response(status=204, content_type='application/json')

    #removes a user from an organization
    def destroy(self, id=None):
        queryset = self.get_queryset(request, 'send_invitation')
        service = service.organization_users.OrganizationsUsers(self.request, queryset)
        service.delete(pk)
        return Response(status=204, content_type='application/json')

    @action(detail=False, methods=['POST'])
    def send_invitation(self, request):
        queryset = self.get_queryset(request, 'send_invitation')
        service = services.organization_users.OrganizationsUsers(self.request, queryset)
        serializer = serializers.serializer.SendInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service.send_invite()
        return Response(status=204, content_type='application/json')
    
    @action(detail=False, methods=['GET'])
    def activate_invite(self, request, token):
        queryset = self.get_queryset(request, UserViewSet, 'activate_invitation')
        service = services.users.Users(self.request, queryset)
        user = service.activate_invitation(token=token)
        #get the password reset link token url from auth0
        client_id = os.environ.get('auth0_client_id')
        client_secret = os.environ.get('auth0_client_secret')
        ath = services.auth0.Auth0ManagmentAPI(client_id, client_secret)
        invite_redirect = ath.get_passsword_reset_url_by_id(user.auth0_id, invite_url=True)
        return HttpResponseRedirect(redirect_to=invite_redirect)

#endpoint for managing users
class UserViewSet(AccessViewSetMixin, ModelViewSet_):
    
    access_policy = UsersAccessPolicy

    #lists all the streams of the users organization 
    def list(self, request):
        serializer = serializers.GenericListSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        organization_id = serializer.validated_data.get('organization_id')
        queryset = self.get_queryset(request, 'list', organization=organization_id)
        service = services.users.Users(self.request, queryset)
        #get all users organizatins 
        users = service.all()
        data = UsersSerializer(users, many=True)
        return Response(data, status=200, content_type='application/json')

    #creates an user
    def create(self, request):
        queryset = self.get_queryset(request, 'create')
        permissed_orgs = self.permissed_orgs(request, 'create')
        service = services.users.Users(self.request, queryset, permissed_orgs)
        serializer = serializers.UserSerializer(data=request.data, context={"service": service})
        serializer.is_valid(raise_exception=True)
        data = serializer.save().data
        return Response(data, status=200, content_type='application/json')

    #retrieves a user
    def retrieve(self, request, pk):
        queryset = self.get_queryset(request, 'retrieve')
        service = services.users.Users(self.request, queryset)
        user = service.get_or_raise(pk)
        data = UserSerializer(user).data
        return Response(data, status=200, content_type='application/json')
    
    #updates an existing user
    def update(self, request, pk):
        queryset = self.get_queryset(request, 'update')
        service = services.users.Users(self.request, queryset)
        serializer = serializers.UserSerializer(data=request.data, context={"service": service})
        serializer.is_valid(raise_exception=True)
        serializer.update(pk)
        return Response(status=204, content_type='application/json')
    
    #deletes a user
    def destroy(self, request, pk):
        queryset = self.get_queryset(request, 'destroy')
        service = services.users.Users(self.request, queryset)
        service.delete(pk)
        return Response(status=204, content_type='application/json')


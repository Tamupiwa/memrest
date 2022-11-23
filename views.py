import requests 
import http.client
import json
from django.shortcuts import render
from rest_framework.exceptions import *
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_access_policy import AccessViewSetMixin
from api.permissions.roles import *
from api import serializers
from django.conf import settings
from rest_framework.response import Response
from authlib.integrations.django_oauth2 import ResourceProtector
from django.http import JsonResponse
import os
import auth0

require_oauth = ResourceProtector()
validator = auth0_validator.Auth0JWTBearerTokenValidator(
    os.environ['AUTH0_DOMAIN'],
    os.environ['AUTH0_IDENTIFIER']
)
require_auth.register_token_validator(validator)

#overides model viewset to include getting scoped queryset and permissioned orgs 
class ModelViewSet_(viewsets.ModelViewSet):
    
    #returns existing resources users has permission
    def get_queryset(self, request, action, organization_id=None):
        return self.access_policy().scope_queryset(
            request=request,
            action=action,
            role_scoped=True,
            organization_id=organization_id)

    #used to get organizations user has permmission to access and edit resources for
    def permissed_orgs(self, request, action, organization_id=None):
        return self.access_policy().get_permissioned_organizations(
            request=request, 
            action=action,
            role_scoped=True,
            organization_id=organization_id)

    
 class UsersViewSet(AccessViewSetMixin, PermissionedModelViewSet):
    
    access_policy = UsersAccessPolicy

    #lists all the streams of the users organization
    def list(self, request):
        serializer = serializers.GenericListSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        organization_id = serializer.validated_data.get('organization_id')
        self.queryset = self.get_queryset(request, 'list', organization_id=organization_id)
        service = services.users.UserService(self.request, self.queryset)
        #get all users organizatins 
        users = service.all()
        data = serializers.UserSerializer(users, many=True).data
        return Response(data, status=200, content_type='application/json')

    #retrieves a user
    def retrieve(self, request, pk):
        self.queryset = self.get_queryset(request, 'retrieve')
        service = services.users.UserService(self.request, self.queryset)
        user = service.get_or_raise(pk)
        data = serializers.UserSerializer(user).data
        return Response(data, status=200, content_type='application/json')
    
    #updates an existing user
    def update(self, request, pk):
        self.queryset = self.get_queryset(request, 'update')
        service = services.users.UserService(self.request, self.queryset)
        serializer = serializers.UserUpdateSerializer(data=request.data, context={"service": service})
        serializer.is_valid(raise_exception=True)
        serializer.update(pk, serializer.validated_data)
        return Response(status=204, content_type='application/json')
    
    #deletes a user
    def destroy(self, request, pk):
        self.queryset = self.get_queryset(request, 'destroy')
        service = services.users.UserService(self.request, self.queryset)
        service.delete(pk)
        return Response(status=204, content_type='application/json')
    
#endpoint for managing organizations
class OrganizationsViewSet(AccessViewSetMixin, ModelViewSet_):
    access_policy = OrganizationsAccessPolicy

    #lists all users organizations 
    def list(self, request):
        self.queryset = self.get_queryset(request, 'list')
        service = services.organizations.OrganizationService(self.request, self.queryset)
        organizations = service.all()
        data = serializers.OrganizationSerializer(organizations, many=True).data
        return Response(data, status=200, content_type='application/json')

    #creates a new organization
    def create(self, request):
        self.queryset = self.get_queryset(request, 'create')
        permissed_orgs = self.permissed_orgs(request, 'create')
        service = services.organizations.OrganizationService(self.request, queryset, permissed_orgs)
        serializer = serializers.OrganizationSerializer(data=request.data, context={"service": service})
        serializer.is_valid(raise_exception=True)
        org = serializer.save()
        data = serializers.OrganizationSerializer(org).data
        return Response(data, status=200, content_type='application/json')

    #retrieves an organization
    def retrieve(self, request, pk):
        self.queryset = self.get_queryset(request, 'retrieve')
        service = services.organizations.OrganizationService(self.request, self.queryset)
        organization = service.get_or_raise(pk)
        data = serializers.OrganizationSerializer(organization).data
        return Response(data, status=200, content_type='application/json')
    
    #updates an existing organization
    def update(self, request, pk):
        self.queryset = self.get_queryset(request, 'update')
        service = services.organizations.OrganizationService(self.request, self.queryset)
        serializer = serializers.OrganizationUpdateSerializer(data=request.data, context={"service": service})
        serializer.is_valid(raise_exception=True)
        serializer.update(pk, serializer.validated_data)
        return Response(status=204, content_type='application/json')

    #archives an organization
    def destroy(self, request, pk):
        self.queryset = self.get_queryset(request, 'delete')
        service = services.organizations.OrganizationService(self.request, self.queryset)
        service.delete(pk)
        return Response(status=204, content_type='application/json')


#endpoint for managing organization memberships (relationships between an organization and its users. organization/<id>/users/<id )
class OrganizationMembershipViewSet(AccessViewSetMixin, PermissionedModelViewSet):
    access_policy = OrganizationMembershipsAccessPolicy
            
    #lists all users in the organization and their organizational meta data
    def list(self, request):
        #get all memberships
        serializer = serializers.GenericListSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        organization_id = serializer.validated_data.get('organization_id')
        self.queryset = self.get_queryset(request, 'list', organization_id)
        service = services.organization_memberships.OrganizationMembershipService(self.request, self.queryset)
        memberships = service.all(serializer.validated_data)
        data = serializers.OrganizationMembershipSerializer(memberships, many=True).data
        return Response(data, status=200, content_type='application/json')

    #creates organization membership and sends an invite email to the user
    def create(self, request):
        self.queryset = self.get_queryset(request, 'send_invite')
        service = services.organization_memberships.OrganizationMembershipService(self.request, self.queryset)
        serializer = serializers.SendInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service.send_invite(serializer.validated_data)
        return Response(status=204, content_type='application/json')

    #retrieves a organization membership
    def retrieve(self, request, pk):
        self.queryset = self.get_queryset(request, 'retrieve')
        service = services.organization_memberships.OrganizationMembershipService(self.request, self.queryset)
        #gets organization and validates user belongs to organization
        membership = service.get_or_raise(pk)
        data = serializers.OrganizationMembershipSerializer(membership).data
        return Response(data, status=200, content_type='application/json')
    
    #updates an existing organization membership
    def update(self, request, pk):
        self.queryset = self.get_queryset(request, 'update')
        service = services.organization_memberships.OrganizationMembershipService(self.request, self.queryset)
        serializer = serializers.OrganizationMembershipUpdateSerializer(data=request.data, context={'service': service})
        serializer.is_valid(raise_exception=True)
        serializer.update(pk, serializer.validated_data)
        return Response(status=204, content_type='application/json')

    #removes a user from an organization membership
    def destroy(self, request, pk):
        self.queryset = self.get_queryset(request, 'retrieve')
        service = services.organization_memberships.OrganizationMembershipService(self.request, self.queryset)
        service.delete(pk)
        return Response(status=204, content_type='application/json')
   
class AuthViewSet(AccessViewSetMixin, PermissionedModelViewSet):
    access_policy = AuthAccessPolicy
    authentication_classes = []
    permission_classes = []

    def list(self, request):
        return Response({'detail': 'List method unsuported'}, status=405, content_type='application/json')

    #takes clients client_id, client_secret and returns an access token from auth0 for client credentials flow
    def create(self, request):
        serializer = serializers.AuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client_id = serializer.validated_data['client_id']
        client_secret = serializer.validated_data['client_secret']
        conn = http.client.HTTPSConnection(settings.AUTH0_DOMAIN)
        payload = {"client_id": client_id, "client_secret": client_secret, "audience": settings.AUTH0_API_AUDIENCE, "grant_type": "client_credentials"}
        payload = json.dumps(payload)
        headers = { 'content-type': "application/json" }
        conn.request("POST", "/oauth/token", payload, headers)
        res = conn.getresponse()
        if res.status == 200:
            data = res.read()
            data = data.decode("utf-8")
            data = json.loads(data)
            return Response(data, status=200, content_type='application/json')

        return Response({'Detail': 'Invalid credentials'}, status=401, content_type='application/json')
    
    def retrieve(self, request, pk):
        return Response({'detail': 'Retrieve method unsuported'}, status=405, content_type='application/json')
    
    def update(self, request, pk):
        return Response({'detail': 'Update method unsuported'}, status=405, content_type='application/json')

    def destroy(self, request, pk):
        return Response({'detail': 'Delete method unsuported'}, status=405, content_type='application/json')


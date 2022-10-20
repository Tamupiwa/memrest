from api.models import OrganizationMembership, User, Organization
from api.services.auth0 import Auth0ManagmentAPI
from api.services.base_service import BaseService
from rest_framework.exceptions import *

#Contains all base  for all model services
class BaseService:
    
    #validates user can create resource for organization passed in request body
    #since this action permission cannot be provisioned using the scoped queryset since the resource doesnt exist yet
    def validate_create_permission(self, organization_id):
        if organization_id not in self.permissed_orgs:
            raise NotFound('Organization not found')
            


from api.models import OrganizationMembership, User, Organization
from api.utilities.auth0 import Auth0ManagmentAPI
from api.services.base_service import BaseService
from rest_framework.exceptions import APIException, NotFound, PermissionDenied
from django.db import transaction
import os
'''
Handles logic for the user endpoint

'''
class UserService(BaseService):
    def __init__(self, request=None, queryset=None, permissed_orgs=None):
        self.request = request
        self.scoped_queryset = self.unarchived_queryset(queryset) if queryset else None
        self.permissed_orgs = permissed_orgs

    #returns all users of a users organization
    def all(self):
        return self.scoped_queryset

    #creates a new user in db and in auth0
    def create(self, email, password, first_name, last_name, organization_id, role, is_key_contact):
        client_id = os.environ.get('auth0_client_id')
        client_secret = os.environ.get('auth0_client_secret')
        ath = Auth0ManagmentAPI(client_id, client_secret)
        auth0_user_id = (ath.create_user(email=email, password=password,
                                        validate_email=True))
        user = (User.objects.create_user(first_name=first_name, last_name=last_name, role=role,
                                        is_key_contact=is_key_contact, auth0_id=auth0_user_id))
        organization = organization.objects.get(id=organization_id)
        user.organization.add(role=role, is_key_contact=is_key_contact)
        return user

    #return a specific user if their within their organization
    def get(self, user_id):
        if not self.scoped_queryset:
            return False
            
        user = self.scoped_queryset.filter(id=user_id)
        if user.exists():
            return user[0]
        else:
            return False
    
    #returns a user if it belongs to a users organizations otherwise raises an error 
    def get_or_raise(self, user_id):
        user = self.get(user_id)
        if not user:
            raise NotFound('User not found.')
        
        return user

    def update(self, user_id, validated_data):
        instance = self.get_or_raise(user_id)
        for key, value in validated_data.items():
            setattr(instance, key, value)

        instance.save()
        return instance

    #deletes a user 
    def delete(self, user_id):
        with transaction.atomic():
            #validate user exists
            user = self.get_or_raise(user_id)
            #validates user isnt the sole admin in any of their organizations, 
            # if they are do not allow user to be deleted until they asign admin to someone else or if 
            # the entire organization is being deleted (archived)
            self.validate_not_sole_admin(user_id)
            client_id = os.environ.get('auth0_client_id')
            client_secret = os.environ.get('auth0_client_secret')
            ath = Auth0ManagmentAPI(client_id, client_secret)
            ath.delete_user(user.auth0_id)
            user.delete()
    
    #checks if user is within an organization that is archived
    def unarchived_queryset(self, queryset):
        archived_orgs_users = User.objects.filter(organizations__archived=True).values_list('id', flat=True)
        return queryset.exclude(id__in=archived_orgs_users)

    #returns all organizations
    def all_organizations(self, user_id):
        organization_ids = OrganizationMembership.objects.filter(user__id=user_id).values_list(organization__id, flat=True)
        return Organization.objects.filter(id__in=organization_ids)

    #checks if user is the sole admin in any of their organizations 
    def validate_not_sole_admin(self, user_id):
        #users organizations in which they are an admin
        users_orgs = OrganizationMembership.objects.filter(user=user_id, role="Organization admin").values_list('organization__id', flat=True)
        #get other users in users organizations
        users_orgs_all_users = OrganizationMembership.objects.filter(organization__id=users_orgs)
        #do not delete if user belongs to an organization where they are the sole admins
        #for each organization a user belongs to check if they are the sole admins
        for org_id in users_orgs:
            total_org_admins = len(users_orgs_all_users.filter(id=org_id, role="Organization admin") )
            admin_membership = users_orgs_all_users.filter(id=org_id, user__id=user_id, role= "Organization admin")
            #if user is an admin for the org check if user is the sole admin 
            if admin_membership.exists():
                if admin_membership.filter(organization__archived__is_null=True) and total_org_admins == 1:
                    raise PermissionDenied()

 


from django.db.models import Q
from django.db import transaction
from rest_framework.exceptions import *
from api.models import Organization, User, OrganizationMembership
from api.services.base_service import BaseService
import requests

class OrganizationService(BaseService):
    def __init__(self, request=None, queryset=None, permissed_orgs=None):
        self.request = request
        self.scoped_queryset = self.unarchived_queryset(queryset) if queryset else None
        self.permissed_orgs = permissed_orgs

    #returns all organizations user belong to
    def all(self):
        return self.scoped_queryset

    def create(self, validated_data):
        org = Organization.objects.create(**validated_data)
        return org

    #returns an organization if the user belongs to the organization
    def get(self, organization_id):
        if not self.scoped_queryset:
            return False
            
        if not self.scoped_queryset:
            return False

        org = self.scoped_queryset.filter(id=organization_id)
        if org.exists():
            return org[0]
        else:
            return False

    #eturns an organization if it belongs to a users organizations otherwise raises an error 
    def get_or_raise(self, organization_id ):
        org = self.get(organization_id)
        if not org:
            raise NotFound()
        
        return org

    def update(self, organization_id, validated_data):
        organization = self.get_or_raise(organization_id)
        for key, value in validated_data.items():
            setattr(organization, key, value)
            organization.save()

        return organization

    #archives an organization and removes identifiable information 
    #.. Note: users and their auth0 accounts belonging to an organization are removed periodically using a task scheduler as it may take a long time.
    #.. auth0 account is only deleted if user only belongs to that organization and no others)
    def delete(self, organization_id):
        organization = self.get_or_raise(organization_id)
        with transaction.atomic():
            #remove all identifiable information from organization and mark their account as archived
            organization.name='archived'
            organization.archived=True
            #if any of organization users don't belong to any other organization mark their account as inactive
            organization_users = OrganizationMembership.objects.filter(organization_id=organization_id).values_list('user_id', flat=True)
            for user_id in organization_users:
                memberships = (OrganizationMembership.objects
                        .filter(user__id=user_id))
                
                total_memberships = len(memberships)
                if total_memberships == 1:
                    User.objects.filter(id=user_id).update(is_active=False)

            #delete all goals and milestones (milestones are auto deleted using cascade)
            goals = Goal.objects.filter(organization_id=organization_id)
            goals.delete()
            organization.save()
            #trigger task runner job to delete user/auth0 accounts without waiting for response to prevent hanging the api 
            #... note: job is run periodically anyway so reliability is not a concern for this hacky solution 
            try:
                pass
                #*** get correct the url
                #requests.get("yourdomain.com/jobs/remove-users", timeout=0.0000000001)
            except requests.exceptions.ReadTimeout: 
                pass


    #returns unarchived organization(s) from scoped queryset
    def unarchived_queryset(self, queryset):
        return queryset.filter(archived=False)



from django.db.models import Q
from itsdangerous import Serializer
from django.template.loader import render_to_string
from django.template.loader import render_to_string
from api.models import Organization, User, OrganizationMembership
from api.services.auth0 import Auth0ManagmentAPI
from django.contrib.auth.models import User, Group
from api.services.base_service import BaseService

class OrganizationMembershipService(BaseService):
    def __init__(self, request=None, queryset=None, permissed_orgs=None):
        self.request = request
        self.scoped_queryset = self.unarchived_queryset(queryset) if queryset else None
        self.permissed_orgs = permissed_orgs

    #returns all users of an organization
    def all(self):        
        return self.scoped_queryset

    #returns an organization if it belongs to a users organizations
    def get(self, membership_id):
        if not self.scoped_queryset:
            return False
            
        org_user = self.scoped_queryset.filter(id=membership_id)
        if org_user.exists():
            return org_user[0]
        else:
            return False

    #returns an organization user if it belongs to a users organizations otherwise raises an error 
    def get_or_raise(self, organization_id):
        org = self.get(organization_id)
        if not org:
            raise NotFound('Membership not found')
        
        return org

    def update(self, membership_id, validated_data):
        org_member= self.get_or_raise(membership_id)
        for key, value in validated_data.items():
            setattr(org_member, key, value)
        org_member.save()
        return org_member

    #removes a user from a role in djangos built-in permission group
    def remove_user_from_role_permission_group(self, user, role):
        #if users only holds this role for a single organization remove role from role permission group
        users_roles = OrganizationMembership.objects.filter(user=user, role=role)
        if len(users_roles) == 1:
            user.groups.filter(name=role).delete()

    #adds a user to role permission group in djangos built-in permission
    def add_user_to_role_permission_group(user, role):
        user_group = user.groups.filter(role=role)
        #if user isnt already in the 
        if not user_group.exists():
            user.group.add(role=rolel)

    #remove a user from an organization
    def delete(self, membership_id):
        with transaction.atomic():
            #check organization exists and belongs to users organizations
            organization_user = self.get_or_raise(membership_id)
            #do not delete user if there is no other admin in the organization
            if organization_user.role == 'Organization Admin':
                raise ParseError('Another admin must be assigned before user can be removed from organization')

            #remove userorganization record
            organization_user.delete()
            #remove user from role permission group
            self.remove_user_to_role_permission_group(user, organization_user['role'])
            client_id = os.environ.get('auth0_client_id')
            client_secret = os.environ.get('auth0_client_secret')
            ath = Auth0ManagmentAPI(client_id, client_secret)
            User.objects.filter(id=organization_user['user__id']).delete()
             
    #filters scoped queryset for unarchived memberships only
    def unarchived_queryset(self, queryset):
        return queryset.objects.filter(organization__archived=False)

    #checks that permissions tags are valid
    def validate_permissions(self, permissions):
        for perm in permissions:
            try:
                Tag.objects.get(perm['tag_id'])
            except:
                raise NotFound('Tag for permission not found.')

     #creates a user invite link that expires after 7 days
    def create_invite_token(self, organization_id, first_name, last_name, email, expires, is_external, permissions):
        secret = os.environ.get('django_secret_key')
        s = Serializer(secret, 60*60*24*7)
        token = s.dumps(
                {
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'organization_id': organization_id,
                    'expires': expires,
                    'is_external': is_external,
                    'permissions': permissions
                }).decode('utf-8')
        return token

    #send invite link to invitees email
    def send_invite(self, organization_id, user_id, sender_email, sender_name, to_email, expires, is_external, permissions):
        #check if organization exits for the sending user
        if not OrganizationMembership.objects.filter(user__id=user_id, organization__id=organization_id).exists():
            raise PermissionDenied('Inviter organization not found.')

        #check if tags ids of permissions exists
        self.validated_permissions(permissions)
        token = self.create_invite_token(organization_id, user_id, first_name, last_name, email, expires, is_external, permissions)
        message = render_to_string('invite_email.html', {
            'sender_name': sender_name, 
            'sender_email': sender_email, 
            'domain': 'yourdomain.com',
            'token': token
        })
        email = EmailMessage(subject='Your App Invite', body=message, to=[to_email],from_email='"Your App" <no-reply@yourdomain.com>')
        email.content_subtype = "html"
        email.send(fail_silently=False)

        #creates a django/auth0 user when a user click the inbox invite link 
    def activate_invitation(self, request, token):
        try:
            with transaction.atomic():
                secret = os.environ.get('django_secret_key')
                s = Serializer(secret, 60*60*24*14)
                #user id of admin 
                token_plain = s.loads(token)
                #if the user already has has an account dont create a new account 
                #... linked them to the organization instead
                client_id = os.environ.get('auth0_client_id')
                client_secret = os.environ.get('auth0_client_secret')
                ath = services.auth0.Auth0ManagmentAPI(client_id, client_secret)
                resp = ath.get_user(token_plain['email'])
                #check if user with matching email already exists
                existing_user = resp[0]['user_id']
                if existing_user:
                    user = User.objects.get(auth0_id=existing_user)
                else:
                    user = (User.objects.create( 
                            first_name=token_plain['first_name'], last_name=token_plain['last_name'],
                            timezone=token_plain['timezone']))

                organization = Organization.objects.get(id=token_plain['organization_id'])
                membership = OrganizationMembership.create(
                    user=user, organization=organization, is_key_contact=token_plain['is_key_contact'],
                    role=token_plain['role'])

                #add user to role permission group
                self.add_user_to_role_permission_group(user, membership.role)
                #create User in db and auth0
                password = ''.join(random.choices(string.ascii_letters + string.digits + string.punctuation, k=9))
                user = ath.create(**token_plain, timezone=organization.timezone, validate_email=True, password=password)

                return user,
        except itsdangerous.exc.SignatureExpired:
            raise NotFound()

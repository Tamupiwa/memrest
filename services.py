from django.db.models import Q
from rest_framework.exceptions import *
from django.template.loader import render_to_string
from django.template.loader import render_to_string
from api.models import Organization, User, OrganizationMembership
from django.contrib.auth.models import Group
from api.services.base_service import BaseService
from api.utilities.auth0 import Auth0ManagmentAPI
from django.db import transaction
from django.core.mail import EmailMessage
from api import services
import os
import string
import random

class OrganizationService(BaseService):
    def __init__(self, request=None, queryset=None, permissed_orgs=None):
        self.request = request
        self.scoped_queryset = queryset
        self.permissed_orgs = permissed_orgs

    #returns all organizations user belong to
    def all(self):
        return self.scoped_queryset

    #creates organization and assigns it a facility manager
    def create(self, validated_data):
        with transaction.atomic():
            organization = Organization.objects.create(**validated_data)
                
        return organization

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
        organization.delete()
            
            
class OrganizationMembershipService(BaseService):
    def __init__(self, request=None, queryset=None, permissed_orgs=None):
        self.request = request
        self.scoped_queryset = queryset
        self.permissed_orgs = permissed_orgs

    #returns all users of an organization
    def all(self, validated_data):     
        user_id = validated_data.get('user_id')
        all_memberships = self.scoped_queryset
        if user_id:
            all_memberships = self.scoped_queryset.filter(user__id=user_id)  

        return all_memberships

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
    def add_user_to_role_permission_group(self, user, role):
        role_permission = user.groups.filter(name=role)
        #if user isnt already in the permission group for the role
        if not role_permission.exists():
            role_group = Group.objects.get(name=role)
            user.groups.add(role_group)

    #remove a user from an organization
    def delete(self, membership_id):
        with transaction.atomic():
            #check organization exists and belongs to users organizations
            membership = self.get_or_raise(membership_id)
            role = membership.role
            user_id = membership.user_id
            membership_id = membership.id
            #users total memberships
            total_memberships = len(OrganizationMembership.objects.filter(user_id=user_id))

            #do not delete user if there is no other admin in the organization
            if membership.role == 'admin' and len(OrganizationMembership.objects.filter(organization_id=membership.organization_id, role='admin') == 1):
                raise ParseError('Another admin must be assigned before user can be removed from organization')

            #remove membership
            membership.delete()
            #remove user from role permission group
            user = User.objects.get(id=user_id)
            self.remove_user_from_role_permission_group(user, role)

            #if user only has one membership also delete the user
            if total_memberships == 1:
                client_id = os.environ.get('AUTH0_CLIENT_ID')
                client_secret = os.environ.get('AUTH0_CLIENT_SECRET')
                ath = Auth0ManagmentAPI(client_id, client_secret)
                ath.delete_user(user.auth0_id)
                user.delete()
    
    def send_invite(self, validated_data):
        with transaction.atomic():
            #membership within organization invite is coming from e.g microsoft admin inviting a employee
            # #.. the sending_member_id ther microsoft admin membership
            sending_member_id = validated_data['sending_member_id']
            first_name = validated_data['first_name'].title()
            last_name = validated_data['last_name'].title()
            email = validated_data['to_email']
            role = validated_data['role']
            expires = validated_data['expires']
            is_external = validated_data['is_external']
            is_key_contact = validated_data['is_key_contact']

            #validate role is in the list of  available roles (this is validated by the serializer but 
            # is CRITICAL so we validate it here too since assigning a user as support or system admin would be disasterious)
            if role not in ['admin', 'user']:
                raise ValidationError({"role": ["Invalid role type selected"]})

            #gets/validates sending member
            sending_member = OrganizationMembership.objects.get(id=sending_member_id, user_id=self.request.user.id)
            sending_member_org_id = OrganizationMembership.objects.get(id=sending_member_id).organization_id
            sending_member_orgs_facility_manager = sending_member.organization.facility_manager

            #only create new user/auth0 account if they dont exists
            user = User.objects.filter(email=email)
            client_id = os.environ.get('AUTH0_CLIENT_ID')
            client_secret = os.environ.get('AUTH0_CLIENT_SECRET')
            domain = os.environ.get('AUTH0_DOMAIN')
            ath = Auth0ManagmentAPI(client_id, client_secret, domain)

            if not user.exists():
                new_user = True
                full_name = '{} {}'.format(first_name, last_name)
                password = ''.join(random.choices(string.ascii_letters + string.digits + string.punctuation, k=9))
                auth0_id = ath.create_user(email, full_name, password)
                user = (User.objects.create_user( 
                    email=email, password=password, is_active=True,
                    auth0_id=auth0_id, first_name=first_name, last_name=last_name,
                    timezone=self.request.user.timezone))

            else:
                new_user = False
                user = user.first()
                auth0_id = user.auth0_id
                self.validate_existing_membership(sending_member_org_id, user.id, role)

            organization = Organization.objects.get(id=sending_member_org_id)
            OrganizationMembership.objects.create(
                role=role, expires=expires, is_external=is_external, is_key_contact=is_key_contact,
                user=user, organization=organization)


            #add user to role permission group
            self.add_user_to_role_permission_group(user, role)

            #if this is a newly created user create auth0 password reset link otherwise, just make redirect link to the login page
            if new_user:
                redirect_url = ath.get_passsword_reset_url_by_id(auth0_id, invite_url=True)
            else: 
                redirect_url = settings.HOME_URL

            message = render_to_string('invite_email.html', {
                'sender_name': '{} {}'.format(self.request.user.first_name, self.request.user.last_name), 
                'sender_email': self.request.user.email, 
                'domain': settings.DOMAIN,
                'redirect_url': redirect_url
            })
            email = EmailMessage(subject='Method InSight Invite', body=message, to=[email],from_email='<no-reply@' + settings.DOMAIN)
            email.content_subtype = "html"
            email.send(fail_silently=False)
    
    #validates user doesnt have an existing membership for the same role
    def validate_existing_membership(self, organization_id, user_id, role):
        if OrganizationMembership.objects.filter(
            user=user_id, role=role,
            organization_id=organization_id).exists():

            raise Exception('User has an existing account with this role already.')

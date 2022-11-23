from api.models import *
from rest_access_policy import AccessPolicy
from api.utilities import utilities


'''
All permissions pertaining to role access policies for each endpoint
Permissions are deny by default. Any deny effect overides all the allow effects.
IMPORTANT: We use a whitelisting as the design philosphy for declaring permissions. Furthermore, 
- meaning only 'allow' statements should be declared since permission is deny by default. 
- Only permission groups should be defined as principals in each policy statement. 
- All statement actions and principals should be lists
- * delimeter to include all actions should only be used with the assumption that new methods
will be added to the viewset in the future otherwise each action should be explicitly listed
 
If this isnt followed the entire permissions system breaks
Available permissions groups: 
    - Admin
    - User

'''

#NOTE: 'Admin' and 'user' groups must be created in Django.contrib.auth.Group model and assigned to users to allow this to work
class BaseAccessPolicy:

    def get_permissioned_organizations(self, request, role_scoped, action=None, organization_id=None):
        #if permissions are role scoped get users permissed organizations for the action, otherswise get permissed orgs for all actions
        if role_scoped:
            permissed_orgs = self.permissioned_organizations_by_role(request, action)
        else:
            permissed_orgs = OrganizationMembership.objects.filter(user__id=request.user.id).values_list('organization__id', flat=True)

        #if user is a system admin give them permission for all organization resources
        if OrganizationMembership.objects.filter(user_id=request.user.id, role="Admin"):
            permissed_orgs = Organization.objects.values_list('id', flat=True)

        #if permissed queryset is only being sought for a set of organizations (list )
        #only return resources for that set of organizations from users permissed organizations
        if organization_id:
            #incase it a comma seperated with more than one value
            organization_ids = str(organization_id).split(',')
            permissed_orgs = [p for p in permissed_orgs if p in organization_ids]
        
        return list(permissed_orgs)
    
    def permissioned_organizations_by_role(self, request, action):
        permissioned_orgs = []
        #get permissed orgs for all actions if action is not specified otherwise filter only statements with the requested action
        statements = self.statements if not action else [s for s in self.statements if action in s['action'] or '*' in s['action']]
        #all of users org membership roles
        memberships = OrganizationMembership.objects.filter(user__id=request.user.id).values('role', 'organization__id')
        #iterate each of users role and check if the role is included in any of the policy statements
        for membership in memberships:
            role = membership['role']
            org_id = membership['organization__id']
            for statement in statements:
                #check if the role is in any of the statement principals
                role_in_policy = True if '*' in statement['principal'] else any(role in principal for principal in statement['principal'])
                #check if the roles is in an allowed policy add the roles organization to permissable organizations for the action
                if role_in_policy and statement['effect'] == "allow":
                    permissioned_orgs.append(org_id)

        return permissioned_orgs

#--------------- Organizations --------------------


#all role based policies for organizations
class OrganizationsAccessPolicy(AccessPolicy, BaseAccessPolicy):
    statements = [
        {
            "action": ["*"],
            "principal": ['group:Organization admin'],
            "effect": "allow"
        }
    ]
    #A scoped querset returns the resources (organizations in this case) that a user has access to 
    #based on the organizations they have access to the resources determined by their memberships and endpoints group permissionss 
    def scope_queryset(self, request, role_scoped, action=None, organization_id=None):
        permissed_orgs = self.get_permissioned_organizations(request, role_scoped, action, organization_id)
        organizations = Organization.objects.filter(id__in=permissed_orgs)
        return organizations

# -------------- Users ---------------------

#all role based policies for Users
class UsersAccessPolicy(AccessPolicy, BaseAccessPolicy):
    statements = [
        {
            "action": ["*"],
            "principal": ["group:user", "group:admin"],
            "effect": "allow"
        },

    ]
    def scope_queryset(self, request, role_scoped, action=None, organization_id=None):
        permissed_orgs = self.get_permissioned_organizations(request, role_scoped, action, organization_id)
        user_ids = set(OrganizationMembership.objects.filter(organization__id__in=permissed_orgs).values_list('user__id', flat=True))
        users = User.objects.filter(id__in=user_ids)
        return users
 
#--------------- Memberships -----------------------

#all role based policies for Organization users
class OrganizationMembershipsAccessPolicy(AccessPolicy, BaseAccessPolicy):
    statements = [
        {
            "action": ["*"],
            "principal": ["group:admin"],
            "effect": "allow"
        },
        {
            "action": ["retrieve"],
            "principal": ["group:user"],
            "effect": "allow"
        },

    ]
    def scope_queryset(self, request, role_scoped, action=None, organization_id=None):
        permissed_orgs = self.get_permissioned_organizations(request, role_scoped, action, organization_id)    
        organization_members = OrganizationMembership.filter(organization__id=permissed_orgs)
        return organization_members

 #all authentication endpoint access 
class AuthAccessPolicy(AccessPolicy, BaseAccessPolicy):
    statements = [
        {
            "action": ["create"],
            "principal": ["*"],
            "effect": "allow"
        },

    ]
    def scope_queryset(self, request, role_scoped, action=None, organization_id=None):
        pass

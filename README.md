# Memrest
Memrest is a barebones Django REST API that allows you to quickly get a Django application up and runnning with Users, Organizations, Memberships,  automatic role scoped endpoint permissions and role scoped resource partitioning and Oauth 2.0 integration using Auth0. 

## Design Philosophy
Memrest uses a layered design so all permissioning, business logic, Models/Data are seperated in different layers 

***Serializer -> Access Policy/Resource scoper -> Models--> Viewset -> Service***

This design template allows anyone to build REST API's while maintaining a seperation of concerns for all layers of code.

## Usage
1. run `python3 -m venv /path/to/your/envrionment` to create a virtual envrionment
2. cd to the environment and run `source bin/activate` to activate the environment 
3. run `pip3 install -r /path/to/your/requirements.txt` to install all the dependencies,
4. Create an auth0 user in your Auth0 tenant dashboard
5. run `python3 manage.py createsuperuser` to create a django super user using the same email as the auth0 user
6. To create the permission groups, add the superuser in the system admin permission group and add the auth0 user id to the django user.
``` 
from django.contrib.auth.models import Group
from api.models import User
for role in ['admin', 'user', 'system admin']:
    Group.objects.create(name=role)
    
group = Groups.objects.get(name='system admin')
user = User.objects.get(email='<YOUR_CREATED_USERS_EMAIL>')
user.groups.add(group)
user.auth0_user_id = <Auth0|user_id>
user.save()
```
6. Create an API in auth0 and create a client application (with auth0 database connection and enabled access to the API in the apps settings).
8. run `python3 manage.py runserver` to run API locally on port 8000 at http://127.0.0.1:8000/.

## Adding new endpoints
New Endpoints can easily be added by following the design conventions of the base template.

1. Define an access policy for the Endpoint in policies.py for all membership roles 
2. Define a viewset for the new resource 
3. Define a serializer for the resource
4. Define a service for the new resource
5. Define a Model for the resource
6. Add the viewset to the urls

For example the Base Users endpoints in the base template containts the folowing
1. Access policy -> UsersAccessPolicy
2. Viewset -> UsersViewSet
3. Serializer -> UsersSerializer
4. Service -> UsersService
5. Model -> UserModel


## Creating an Access policy

Access policies restrict users to ViewSets/endpoint methods based on their roles defined by thier organization memberships. Each endpoint is an allow only policy with deny by default. Each access policy must implement a scoped_queryset method which returns a queryset of all the resources a users is
able to read and edit based on the permissed organizations (a list of organizations a user has membership for based on the access policy of the viewset they are trying to access. An access policy is then applied to a ViewSet as below. For more on access policies visit the official library source https://github.com/rsinger86/drf-access-policy 
```

class BooksAccessPolicy(AccessPolicy, BaseAccessPolicy):
    statements = [
        {
            "action": ["list", "retrieve"],
            "principal": ["group:user"],
            "effect": "allow"
        },
        {
            "action": ["*"],
            "principal": ["group:admin"],
            "effect": "allow"
        },

    ]
    
    def scope_queryset(self, request, role_scoped, action=None, organization_id=None):
        permissed_orgs = self.get_permissioned_organizations(request, role_scoped, action, organization_id)
        organizations = Organization.objects.filter(id__in=permissed_orgs)
        return organizations
   
   
class StationsViewSet(AccessViewSetMixin, PermissionedModelViewSet):
    access_policy = BooksAccessPolicy
    
    def list(self, request):
  ... 
  
```

## Auth0 Integration admin information
Everytime a new user requests direct API access, a new m2m client application with client credential grant type must enabled must be created in Auth0 either using the Auth0ManagementAPI or in the web dashboard.
Furthermore since access tokens using client-credentials flow are not connected to the client app and do not have any direct link any auth0 user we must also supply the new client application metadata with the following keys
so that Django knows which user to authenticate and pass to the request.user object during authentication in the custom Auth0 authentication backend. A new Client m2m app is not required for new users authenticating to the API via a SPA (vue.js/react.js) since the Authorization flow is used and the user information is passed during the flow.

**user_email**: 'dummy@dummy.com' <br />
**auth0_user_id**: 'auth0|abcd123'

    
Naming convention for the application must be the user_email (user_id) <br />
e.g dummy@dummy.com (52de3b66-759f-4dd8-954b-d3970576b387)


## Dependencies
- django
- djangorestframework
- drf-access-policy 
- pytest-django
- auth0-python
- drf-nested-routers
- python-jose


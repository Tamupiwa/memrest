# Memrest
Memrest is a barebones Django REST API that allows you to quickly get a Django application up and runnning with Users, Organizations, Memberships,  automatic role scoped endpoint permissioning and resource partitioning and Oauth 2.0 integration using Auth0. 

## Design Philosophy
Memrest uses a layered design so all permissioning, business logic, Models/Data are seperated in different layers 

***Serializer -> Access Policy/Resource scoper -> Models--> Viewset -> Service***

This design template allows anyone to build REST API's while maintaining a seperation of concerns for all layers of code.

## Usage

```
Define an access policy for the Viewset in policies.py for all membership roles 

class UsersAccessPolicy(AccessPolicy, BaseAccessPolicy):
    statements = [
        {
            "action": ["*"],
            "principal": ["group:Organization admin"],
            "effect": "allow"
        },

    ]
  ... 
```


## Dependencies
- django
- djangorestframework
- drf-access-policy 
- pytest-django
- auth0-python
- drf-nested-routers
- Authlib


# Memrest
Memrest is a barebones Django REST API that allows you to quickly get a Django application up and runnning with  Users, Organizations, Memberships,  automatic role based endpoint/resource/queryset permissioning and an Oauth 2.0 (Auth0) wrapper. 

## Design Philosophy
Memrest uses a layered design so all permissioning, business logic, Models/Data are seperated in different layers 

__ Serializer -> Access Policy -> Models/Scoped Queryset --> Viewset -> Service __

This design template allows for developers to build REST API's while maintaining a seperation of concerns for all layers of code.

## Dependencies
- django
- djangorestframework
- drf-access-policy 
- pytest-django
- auth0-python
- drf-nested-routers


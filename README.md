# Memrest
Memrest is a barebones Django REST API that allows you to quickly get a Django application up and runnning with  Users, Organizations, Memberships,  automatic role based endpoint/resource/queryset permissioning and an Oauth 2.0 (Auth0) wrapper. 

Memrest uses a layered design so all permissioning, business logic, Models/Data are seperated in different layers 

Serializer -> Access Policy -> Scoped Queryset --> Viewset -> Service -> Model 

This design template allows for developers to build REST API's while maintaining a seperation of concerns for all layers of code.

# Memrest
MemRest is a barebones Django REST API that allows you to quickly get a Django application up and runnning with  Users, Organizations, Memberships,  automatic role based endpoint/resource/queryset permissioning and Oauth 2.0 (Auth0). Memrest uses a layered design so all permissioning, validation, business logic is seperated in different layers Serializer -> Access Policy -> Viewset -> Service -> Model creating a seperation of convern for all layers of code.

from django.contrib import admin
from django.urls import path
from api import views
from api.services import tasks
from rehab import settings
from rest_framework_nested import routers
from django.urls import path, include
#from rest_framework import routers

admin.site.site_header = 'Memrest'
admin.site.site_title = 'Memrest'

router = routers.SimpleRouter(trailing_slash=False)
router.register(r'/auth', views.AuthViewSet, basename='auth')
router.register(r'/organizations', views.OrganizationsViewSet, basename='organizations')
router.register(r'/organization-memberships', views.OrganizationMembershipViewSet, basename='organization-memberships')
router.register(r'/users', views.UsersViewSet, basename='users')

urlpatterns = [
    path('admin12f867de67a1a1689c65cd60907823def0e07b30068f867cc908b896b971dab7/', admin.site.urls)
] 

urlpatterns += router.urls

if settings.DEBUG:
    import debug_toolbar
    urlpatterns.append(path('__debug__/', include(debug_toolbar.urls)))
    

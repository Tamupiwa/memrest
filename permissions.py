from rest_framework import permissions
from authlib.integrations.django_oauth2 import ResourceProtector
from authlib.oauth2.rfc6749.errors import *

class OAuthPermission(permissions.BasePermission, ResourceProtector):
    """
    Ensures request has a valid OAuth token to access the endpoint.

    Inherits from Authlib Django Resource protector to validate all requests access_tokens, this is a work around since 
    the authlib django decorator only works for function based views and class based views which we need
    see https://github.com/lepture/authlib/issues/305#issuecomment-750308921 and the auth0 ticket
    """

    def has_permission(self, request, view):
        try:
            scopes = None
            token = self.acquire_token(request, scopes)
            request.oauth_token = token
            return True
        except:
            return False

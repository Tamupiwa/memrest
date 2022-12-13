import requests
import os
from django.conf import settings
from django.contrib.auth import get_user_model
from jose import jwt
from rest_framework import exceptions
from rest_framework.authentication import (BaseAuthentication,
                                           get_authorization_header)

from api.utilities.auth0 import Auth0ManagmentAPI
from api.models import User

User = get_user_model()

def is_valid_auth0token(token):
    # TODO: remove request and make the `json` file as part of the project to save the request time
    resp = requests.get('https://'+settings.AUTH0_DOMAIN +
                        '/.well-known/jwks.json')
    jwks = resp.json()
    unverified_header = jwt.get_unverified_header(token)
    rsa_key = {}
    for key in jwks['keys']:
        if key['kid'] == unverified_header['kid']:
            rsa_key = {
                'kty': key['kty'],
                'kid': key['kid'],
                'use': key['use'],
                'n': key['n'],
                'e': key['e']
            }
    if rsa_key:
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=settings.AUTH0_ALGORITHMS,
                audience=settings.AUTH0_API_AUDIENCE,
                issuer='https://'+settings.AUTH0_DOMAIN+'/'
            )
            return payload, True
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('token is expired')
        except jwt.JWTClaimsError:
            raise exceptions.AuthenticationFailed(
                'incorrect claims, please check the audience and issuer',
            )
        except Exception as e:
            raise exceptions.AuthenticationFailed(
                'Unable to parse authentication'
            )

    return {}, False


def get_auth0_user_data(token):
    url = 'https://' + settings.AUTH0_DOMAIN + '/userinfo'
    params = {'access_token': token}
    resp = requests.get(url, params)
    data = resp.json()
    return data

def get_auth0_client_application_meta_data(client_id):
    ath = Auth0ManagmentAPI(os.environ.get('AUTH0_CLIENT_ID'), os.environ.get('AUTH0_CLIENT_SECRET'), os.environ.get('AUTH0_DOMAIN'))
    client = ath.get_client_application(client_id)
    return client['client_metadata']

class Auth0TokenAuthentication(BaseAuthentication):
    '''
    Auth0 token based authentication.
    Clients should authenticate by passing the token key in the 'Authorization'
    HTTP header, prepended with the string 'Bearer '.  For example:
        Authorization: Bearer <token data>
    '''

    keyword = 'Bearer'
    err_msg = 'Invalid token headers'

    def authenticate(self, request):
        auth = get_authorization_header(request).split()
        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None

        if len(auth) == 1:
            raise exceptions.AuthenticationFailed(self.err_msg)

        if len(auth) > 2:
            raise exceptions.AuthenticationFailed(self.err_msg)

        token = auth[1]
        return self.authenticate_credentials(token)

    def authenticate_credentials(self, token):
        payload, is_valid = is_valid_auth0token(token)
        if not is_valid:
            raise exceptions.AuthenticationFailed(self.err_msg)

        grant_type = payload.get('gty')
        #if this is for a client credentials flow it will not have a user so we get the admin user the client application is assigned to
        if grant_type == 'client-credentials':
            client_id = payload['azp']
            auth0_email = payload.get('auth0_user_email')
            auth0_user_id = payload.get('auth0_user_id')
            #if the user email and user id where not passed into the token by the auth0 m2m actions script call the management API to get the details from the client app metadata
            if not auth0_email or not auth0_user_id:
                client_meta_data = get_auth0_client_application_meta_data(client_id)
                auth0_email = client_meta_data['user_email']
                auth0_user_id = client_meta_data['auth0_user_id']

            user = User.objects.filter(email=auth0_email, auth0_id=auth0_user_id).last()
        else:
            user_data = get_auth0_user_data(token)
            auth0_email = user_data.get('email')
            auth0_user_id = user_data.get('sub')
            user = User.objects.filter(email=auth0_email, auth0_id=auth0_user_id).last()

        if not user:
            raise exceptions.AuthenticationFailed('Matching user not found for Identity Server user')

        return user, token

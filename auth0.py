from auth0.v3.authentication import GetToken
from auth0.v3.management import Auth0
from auth0.v3.exceptions import Auth0Error
from api.python_common.repeat_timer import RepeatTimer
from api_project import settings

API_KEY_UPDATE_TIME = 79200 #22 hours

class Auth0ManagmentAPI:

    def __init__(self, non_interactive_client_id, non_interactive_client_secret, domain):
        self.client_id = non_interactive_client_id
        self.client_secret = non_interactive_client_secret
        self.domain = domain
        self.run()

    def run(self):
        self._update_Auth0_conection()
        self.update_timer = RepeatTimer(API_KEY_UPDATE_TIME, self._update_Auth0_conection)
        self.update_timer.start()

    def stop(self):
        self.update_timer.cancel()

    # TODO make this function threadsafe                                                                                                        
    def _update_Auth0_conection(self):
        token = self._get_new_Auth0_token()
        self.auth0 = Auth0(self.domain, token)

    def _get_new_Auth0_token(self):
        get_token = GetToken(self.domain)
        try: 
            token = get_token.client_credentials(self.client_id, self.client_secret, 'https://{}/api/v2/'.format(self.domain))
            mgmt_api_token = token['access_token']
            return mgmt_api_token
        except Exception as e:
            print(e) # TODO: Maker this a logger statment


    def list_users(self):
        """
        Gets list of users 

        A list of users
        """
        data = self.auth0.users.list(fields=["email", "name", "picture", "user_id", "app_metadata"], include_totals=False)
        
        for user in data:
            for item in user['app_metadata']:
                user[item] = user['app_metadata'].get(item)
            
            user.pop('app_metadata')

        return data

    def get_user(self, user_id=None, email=None):
        """
        Get user - gets a single user 

        Parameters
        ----------
        user_id : str
            The user ID of the user you want to fetch   
        email : str
            Email of user you want to fecth  
        Returns
        -------
        the users data on success 
        """

        if email:
            fetched_user = self.auth0.users.users_by_email(email=email)
        else:
            fetched_user = self.auth0.users.get(user_id, fields=["email", "name", "picture", "user_id", "app_metadata"])

        #flatten the user stucture  - remove things out of app_metadata and put them as fields
        for item in fetched_user['app_metadata']:
            fetched_user[item] = fetched_user['app_metadata'].get(item)
        fetched_user.pop('app_metadata')

        return fetched_user

        
    def create_user(self, email, name, password, validate_email=False):
        """
        Create user 

        Parameters
        ----------
        email, name, password  : str
            the detials of the new user 
        validate_email : bool
            send the validation email on user creation 
        Returns
        -------
        on success - the user id of the newly created user 
        on failure - None 
        """
        user_body = {
            "email": email,
            "name": name,
            "email_verified": validate_email,
            "connection" : "Username-Password-Authentication",
            "password": password,
        }
        resp = self.auth0.users.create(user_body)
        return resp.get("user_id")


    def delete_user(self, user_id):  
        self.auth0.users.delete(user_id)
        return True

    def get_passsword_reset_url_by_id(self, user_id, invite_url=False):
        request_body = {
            'user_id' : user_id,
            'result_url' : settings.HOME_URL
        }

        resp = self.auth0.tickets.create_pswd_change(request_body,)
        url = resp.get('ticket')
        if(invite_url):
            url += 'invite'
        return url

    def get_email_template(self, template_name):
        """Retrieves an email template by its name.

        Args:
           template_name (str): Name of the email template to get.
              Must be one of: 'verify_email', 'reset_email', 'welcome_email',
              'blocked_account', 'stolen_credentials', 'enrollment_email',
              'change_password', 'password_reset', 'mfa_oob_code'.
        """

        template = self.auth0.email_templates.get(template_name)
        return template.get('body') 

    #returns all clients/applications
    def get_client_application(self, client_id):
        client = self.auth0.clients.get(client_id)
        return client

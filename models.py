from __future__ import unicode_literals
from django.db import models
from django.contrib.auth.models import PermissionsMixin
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import UserManager
from rest_framework.authtoken.models import Token
from api import services
import datetime as dt
import uuid
import os
import uuid

class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        validate_password(password)
        user.set_password(password)
        user.save(using=self._db)
        #create django rest api token for user
        Token.objects.create(user=user)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_active') is not True:
            raise ValueError('Superuser must have is_active=True.')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)

    class User(AbstractBaseUser, PermissionsMixin):
    id = models.CharField(default=uuid.uuid4, primary_key=True, unique=True, max_length=255)
    auth0_id = models.CharField(unique=True, max_length=255)
    email = models.EmailField(validators=[validate_email], unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    timezone = models.CharField(max_length=255, choices=timezone_choices)
    organizations = models.ManyToManyField('Organization', through='OrganizationMembership')
    is_active = models.BooleanField(default=False)
    #A staff member is able to log into the django admin pages
    is_staff = models.BooleanField(default=False)
    is_flagged = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    first_login = models.BooleanField(default=False)
    date_joined = models.DateField(default=dt.datetime.utcnow)
    objects = UserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

class Organization(models.Model):
    subscription_choices = (
        ('Business', 'Business'),
        ('Enterprise', 'Enterprise')
    )
    id = models.CharField(default=uuid.uuid4, primary_key=True, unique=True, max_length=255)
    name = models.CharField(max_length=50)
    #number of employees
    employees = models.CharField(blank=True, null=True, max_length=7)
    country = models.CharField(max_length=255)
    #industry
    industry = models.CharField(choices=industry_choices, max_length=255)
    is_facility_manager = models.BooleanField(default=False)
    #default timezone for whole orgainization. This is set as the first admin users
    #.. timezone at account creation
    timezone = models.CharField(choices=timezone_choices, max_length=255)
    subscription_plan = models.CharField(choices=subscription_choices, max_length=100)
    #should user be included in the external leaderboard 
    #.. (this will allow other organizations to see their waster diversion data on the leaderboard)
    #.. a organizarion with this setting disabled will not be able to see leaderboards consisting of other organizations
    external_leaderboard_enabled = models.BooleanField(default=False)
    stripe_id = models.CharField(max_length=100)
    #if the organizations InSight is deleted this will be set to true
    archived = models.BooleanField(default=False)
    archived_date = models.DateField(blank=True, null=True)
    #the organizations facilities manager
    facility_manager = models.ForeignKey('self', on_delete=models.PROTECT, blank=True, null=True)
    organization_groups = models.ManyToManyField('OrganizationGroup', through='OrganizationGroupMembership')
    date_created = models.DateField(default=dt.datetime.utcnow)

class OrganizationMembership(models.Model):
    role_choices = (
        ('System admin', 'System admin'),
        ('Installer', 'Installer'),
        ('Manufacturer', 'Manufacturer'),
        ('Organization admin', 'Organization admin'),
        ('Facility manager', 'Facility manager'),
        ('Organization user', 'Organization user'),
        ('Support', 'Support')
    )
    id = models.CharField(default=uuid.uuid4, primary_key=True, unique=True, max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE)
    role = models.CharField(choices=role_choices, max_length=18)
    #layout for users dashboard for their organization
    dashboard_layout = models.JSONField(blank=True, null=True)
    #date user was invited to organization
    invite_date = models.DateField(default=dt.datetime.utcnow)
    is_key_contact = models.BooleanField(default=False)
    #is the organization member an internal member of the organization (an employee)
    is_external = models.BooleanField()
    #the date the membership expires
    expires = models.DateField(blank=True, null=True)
    date_created = models.DateField(default=dt.datetime.utcnow)
 

industry_choices = (
    ('Accounting ', 'Accounting '),
    ('Airlines/Aviation', 'Airlines/Aviation'),
    ('Alternative Dispute Resolution', 'Alternative Dispute Resolution'),
    ('Alternative Medicine', 'Alternative Medicine'),
    ('Animation', 'Animation'),
    ('Apparel/Fashion', 'Apparel/Fashion'),
    ('Architecture/Planning', 'Architecture/Planning'),
    ('Arts/Crafts', 'Arts/Crafts'),
    ('Automotive', 'Automotive'),
    ('Aviation/Aerospace', 'Aviation/Aerospace'),
    ('Banking/Mortgage', 'Banking/Mortgage'),
    ('Biotechnology/Greentech', 'Biotechnology/Greentech'),
    ('Broadcast Media', 'Broadcast Media'),
    ('Building Materials', 'Building Materials'),
    ('Business Supplies/Equipment', 'Business Supplies/Equipment'),
    ('Capital Markets/Hedge Fund/Private Equity', 'Capital Markets/Hedge Fund/Private Equity'),
    ('Chemicals', 'Chemicals'),
    ('Civic/Social Organization', 'Civic/Social Organization'),
    ('Civil Engineering', 'Civil Engineering'),
    ('Commercial Real Estate', 'Commercial Real Estate'),
    ('Computer Games', 'Computer Games'),
    ('Computer Hardware', 'Computer Hardware'),
    ('Computer Networking', 'Computer Networking'),
    ('Computer Software/Engineering', 'Computer Software/Engineering'),
    ('Computer/Network Security', 'Computer/Network Security'),
    ('Construction', 'Construction'),
    ('Consumer Electronics', 'Consumer Electronics'),
    ('Consumer Goods', 'Consumer Goods'),
    ('Consumer Services', 'Consumer Services'),
    ('Cosmetics', 'Cosmetics'),
    ('Dairy', 'Dairy'),
    ('Defense/Space', 'Defense/Space'),
    ('Design', 'Design'),
    ('E-Learning', 'E-Learning'),
    ('Education Management', 'Education Management'),
    ('Electrical/Electronic Manufacturing', 'Electrical/Electronic Manufacturing'),
    ('Entertainment/Movie Production', 'Entertainment/Movie Production'),
    ('Environmental Services', 'Environmental Services'),
    ('Events Services', 'Events Services'),
    ('Executive Office', 'Executive Office'),
    ('Facilities Services', 'Facilities Services'),
    ('Farming', 'Farming'),
    ('Financial Services', 'Financial Services'),
    ('Fine Art', 'Fine Art'),
    ('Fishery', 'Fishery'),
    ('Food Production', 'Food Production'),
    ('Food/Beverages', 'Food/Beverages'),
    ('Fundraising', 'Fundraising'),
    ('Furniture', 'Furniture'),
    ('Gambling/Casinos', 'Gambling/Casinos'),
    ('Glass/Ceramics/Concrete', 'Glass/Ceramics/Concrete'),
    ('Government Administration', 'Government Administration'),
    ('Government Relations', 'Government Relations'),
    ('Graphic Design/Web Design', 'Graphic Design/Web Design'),
    ('Health/Fitness', 'Health/Fitness'),
    ('Higher Education/Academia', 'Higher Education/Academia'),
    ('Hospital/Health Care', 'Hospital/Health Care'),
    ('Hospitality', 'Hospitality'),
    ('Human Resources/HR', 'Human Resources/HR'),
    ('Import/Export', 'Import/Export'),
    ('Individual/Family Services', 'Individual/Family Services'),
    ('Industrial Automation', 'Industrial Automation'),
    ('Information Services', 'Information Services'),
    ('Information Technology/IT', 'Information Technology/IT'),
    ('Insurance', 'Insurance'),
    ('International Affairs', 'International Affairs'),
    ('International Trade/Development', 'International Trade/Development'),
    ('Internet', 'Internet'),
    ('Investment Banking/Venture', 'Investment Banking/Venture'),
    ('Investment Management/Hedge Fund/Private Equity', 'Investment Management/Hedge Fund/Private Equity'),
    ('Judiciary', 'Judiciary'),
    ('Law Enforcement', 'Law Enforcement'),
    ('Law Practice/Law Firms', 'Law Practice/Law Firms'),
    ('Legal Services', 'Legal Services'),
    ('Legislative Office', 'Legislative Office'),
    ('Leisure/Travel', 'Leisure/Travel'),
    ('Library', 'Library'),
    ('Logistics/Procurement', 'Logistics/Procurement'),
    ('Luxury Goods/Jewelry', 'Luxury Goods/Jewelry'),
    ('Machinery', 'Machinery'),
    ('Management Consulting', 'Management Consulting'),
    ('Maritime', 'Maritime'),
    ('Market Research', 'Market Research'),
    ('Marketing/Advertising/Sales', 'Marketing/Advertising/Sales'),
    ('Mechanical or Industrial Engineering', 'Mechanical or Industrial Engineering'),
    ('Media Production', 'Media Production'),
    ('Medical Equipment', 'Medical Equipment'),
    ('Medical Practice', 'Medical Practice'),
    ('Mental Health Care', 'Mental Health Care'),
    ('Military Industry', 'Military Industry'),
    ('Mining/Metals', 'Mining/Metals'),
    ('Motion Pictures/Film', 'Motion Pictures/Film'),
    ('Museums/Institutions', 'Museums/Institutions'),
    ('Music', 'Music'),
    ('Nanotechnology', 'Nanotechnology'),
    ('Newspapers/Journalism', 'Newspapers/Journalism'),
    ('Non-Profit/Volunteering', 'Non-Profit/Volunteering'),
    ('Oil/Energy/Solar/Greentech', 'Oil/Energy/Solar/Greentech'),
    ('Online Publishing', 'Online Publishing'),
    ('Other Industry', 'Other Industry'),
    ('Outsourcing/Offshoring', 'Outsourcing/Offshoring'),
    ('Package/Freight Delivery', 'Package/Freight Delivery'),
    ('Packaging/Containers', 'Packaging/Containers'),
    ('Paper/Forest Products', 'Paper/Forest Products'),
    ('Performing Arts', 'Performing Arts'),
    ('Pharmaceuticals', 'Pharmaceuticals'),
    ('Philanthropy', 'Philanthropy'),
    ('Photography', 'Photography'),
    ('Plastics', 'Plastics'),
    ('Political Organization', 'Political Organization'),
    ('Primary/Secondary Education', 'Primary/Secondary Education'),
    ('Printing', 'Printing'),
    ('Professional Training', 'Professional Training'),
    ('Program Development', 'Program Development'),
    ('Public Relations/PR', 'Public Relations/PR'),
    ('Public Safety', 'Public Safety'),
    ('Publishing Industry', 'Publishing Industry'),
    ('Railroad Manufacture', 'Railroad Manufacture'),
    ('Ranching', 'Ranching'),
    ('Real Estate/Mortgage', 'Real Estate/Mortgage'),
    ('Recreational Facilities/Services', 'Recreational Facilities/Services'),
    ('Religious Institutions', 'Religious Institutions'),
    ('Renewables/Environment', 'Renewables/Environment'),
    ('Research Industry', 'Research Industry'),
    ('Restaurants', 'Restaurants'),
    ('Retail Industry', 'Retail Industry'),
    ('Security/Investigations', 'Security/Investigations'),
    ('Semiconductors', 'Semiconductors'),
    ('Shipbuilding', 'Shipbuilding'),
    ('Sporting Goods', 'Sporting Goods'),
    ('Sports', 'Sports'),
    ('Staffing/Recruiting', 'Staffing/Recruiting'),
    ('Supermarkets', 'Supermarkets'),
    ('Telecommunications', 'Telecommunications'),
    ('Textiles', 'Textiles'),
    ('Think Tanks', 'Think Tanks'),
    ('Tobacco', 'Tobacco'),
    ('Translation/Localization', 'Translation/Localization'),
    ('Transportation', 'Transportation'),
    ('Utilities', 'Utilities'),
    ('Venture Capital/VC', 'Venture Capital/VC'),
    ('Veterinary', 'Veterinary'),
    ('Warehousing', 'Warehousing'),
    ('Wholesale', 'Wholesale'),
    ('Wine/Spirits', 'Wine/Spirits'),
    ('Wireless', 'Wireless'),
    ('Writing/Editing', 'Writing/Editing')
)

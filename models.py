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
    city = models.CharField(max_length=255)
    #industry
    industry = models.CharField(blank=True, null=True, max_length=255)
    #field within the industry
    field = models.CharField(blank=True, null=True, max_length=255)
    #default timezone for whole orgainization. This is set as the first admin users
    #.. timezone at account creation
    timezone = models.CharField(choices=timezone_choices, max_length=255)
    subscription_plan = models.CharField(choices=subscription_choices, max_length=100)
    stripe_id = models.CharField(max_length=100)
    #if the organizations InSight is deleted this will be set to true
    archived = models.BooleanField(default=False)
    date_created = models.DateField(default=dt.datetime.utcnow)

class OrganizationMembership(models.Model):
    role_choices = (
      ('admin', 'admin'),
      ('user', 'user)
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

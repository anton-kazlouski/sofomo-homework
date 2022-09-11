from django.db import models


class Location(models.Model):
    longitude = models.CharField(max_length=100)
    latitude = models.CharField(max_length=100)
    ip = models.CharField(max_length=39, null=True)
    name = models.CharField(max_length=255, unique=True)
    domain = models.CharField(max_length=255, null=True)

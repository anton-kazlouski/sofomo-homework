import re

from decimal import Decimal
from decimal import InvalidOperation

import requests

from .models import Location
from django.conf import settings
from django.core.validators import validate_ipv46_address
from rest_framework import serializers
from rest_framework import status
from rest_framework.exceptions import ValidationError

from .exceptions import ServiceUnavailable
from logging import getLogger

logger = getLogger(__name__)


def get_geo_data(params, path, method="GET", payload={}):
    response = requests.request(
        method,
        path,
        params=params,
        data=payload,
    )
    response_json = response.json()
    if (
        not response_json.get("success", True)
        or response.status_code != status.HTTP_200_OK
    ):
        logger.error(
            "Failed to retreive data from external API: \n response: {}".format(
                response_json
            )
        )
        raise ServiceUnavailable()

    return response.json()


class LocationSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        fields = kwargs.pop("fields", None)
        super().__init__(*args, **kwargs)

        if fields is not None:
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)

    def validate_ip(self, value):
        validate_ipv46_address(value)
        return value

    def validate_domain(self, value):
        if value and not re.match("^[a-z0-9]+\.[a-z0-9]{1,4}$", value):
            raise ValidationError("Please provide valide domain")
        return value

    def validate_latitude(self, value):
        error_text = "Latitude must in range of [-90, 90]"
        try:
            value_dec = Decimal(value)
            if not (value_dec > -90 and value_dec < 90):
                raise ValidationError(error_text)
        except InvalidOperation:
            raise ValidationError(error_text)
        return value

    def validate_longitude(self, value):
        error_text = "Longitude must in range of [-180, 180]"
        try:
            value_dec = Decimal(value)
            if not (value_dec > -180 and value_dec < 180):
                raise ValidationError(error_text)
        except InvalidOperation:
            raise ValidationError(error_text)
        return value

    def create(self, validated_data):
        domain = validated_data.get("domain")
        ip = validated_data.get("ip")

        if not any((ip, domain)) or all((ip, domain)):
            raise ValidationError("Please provide either IP or domain")

        params = {
            "access_key": settings.IPSTACK_KEY,
            "format": 1,
        }
        geo_data = get_geo_data(params, f"{settings.IPSTACK_URL}{ip or domain}")

        geo_data["domain"] = domain
        geo_data["longitude"] = str(geo_data["longitude"])
        geo_data["latitude"] = str(geo_data["latitude"])
        geo_data["name"] = validated_data.get("name")

        serializer = LocationSerializer(data=geo_data)
        serializer.is_valid(raise_exception=True)

        return super().create(serializer.validated_data)

    class Meta:
        model = Location
        fields = [
            "id",
            "longitude",
            "latitude",
            "ip",
            "name",
            "domain",
        ]

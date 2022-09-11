from rest_framework.test import APIClient
from rest_framework.test import APITestCase
from unittest.mock import patch

from mixer.backend.django import mixer
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken

from .models import Location


class LocationViewSetTestCase(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = mixer.blend("auth.User")
        cls.access_token = AccessToken.for_user(cls.user)
        cls.client = APIClient()

    def test_should_return_401_for_any_request_without_token(self):
        for method_name in {"get", "post", "put", "delete"}:
            with self.subTest(method_name):
                method = getattr(self.client, method_name)
                response = method("/locations/")
                self.assertEqual(
                    response.status_code,
                    status.HTTP_401_UNAUTHORIZED,
                )

    @patch("locations.serializers.get_geo_data")
    def test_should_return_201_for_create(self, geo_data_mock):
        geo_data_mock.return_value = {
            "ip": "104.21.233.182",
            "type": "ipv4",
            "continent_code": "NA",
            "continent_name": "North America",
            "country_code": "US",
            "country_name": "United States",
            "region_code": "CA",
            "region_name": "California",
            "city": "San Jose",
            "zip": "95122",
            "latitude": 37.330528259277344,
            "longitude": -121.83822631835938,
            "location": {
                "geoname_id": 5392171,
                "capital": "Washington D.C.",
                "languages": [{"code": "en", "name": "English", "native": "English"}],
                "country_flag": "https://assets.ipstack.com/flags/us.svg",
                "country_flag_emoji": "🇺🇸",
                "country_flag_emoji_unicode": "U+1F1FA U+1F1F8",
                "calling_code": "1",
                "is_eu": False,
            },
        }
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(self.access_token)}")

        domain_payload = {
            "name": "Homepage",
            "domain": "zerkalo.io",
        }
        ip_payload = {
            "name": "ci",
            "ip": "127.203.121.13",
        }
        for p in (ip_payload, domain_payload):
            with self.subTest(p):
                response = self.client.post("/locations/", data=p)
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                response_json = response.json()
                location = Location.objects.get(id=response.json().get("id"))
                self.assertEqual(location.name, response_json["name"])
                self.assertEqual(location.domain, response_json["domain"])
                self.assertEqual(location.ip, response_json["ip"])

    def test_lisst_should_return_200_with_locations(self):
        locations = mixer.cycle(4).blend(Location)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(self.access_token)}")
        response = self.client.get("/locations/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_json = response.json()
        self.assertEqual(len(response_json), 4)
        self.assertListEqual(
            [l["id"] for l in response_json], [l.id for l in locations]
        )

    def test_delete_should_return_204_and_remove_location(self):
        location = mixer.blend(Location)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(self.access_token)}")
        response = self.client.delete(f"/locations/{location.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(Location.objects.filter(id=location.id).exists())

    def test_update_should_return_200_and_update_location(self):
        location = mixer.blend(
            Location,
            latitude=50,
            longitude=-10,
            ip=mixer.faker.ipv4(),
            domain=mixer.faker.dga(),
        )

        payload = {
            "name": "Unicorn",
            "domain": location.domain,
            "ip": location.ip,
            "longitude": location.longitude,
            "latitude": location.latitude,
            "ip": location.ip,
        }

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(self.access_token)}")
        response = self.client.put(f"/locations/{location.id}/", data=payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        location.refresh_from_db()
        self.assertEqual(location.name, "Unicorn")

    def test_get_location(self):
        location = mixer.blend(
            Location,
            latitude=50,
            longitude=-10,
            ip=mixer.faker.ipv4(),
            domain=mixer.faker.dga(),
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(self.access_token)}")
        response = self.client.get(f"/locations/{location.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {
                "id": location.id,
                "longitude": location.longitude,
                "latitude": location.latitude,
                "ip": location.ip,
                "name": location.name,
                "domain": location.domain,
            },
            response.json(),
        )

    @patch("locations.serializers.logger.error")
    @patch("locations.serializers.requests.request")
    def test_should_return_503_if_ipstack_unavailable(
        self,
        mock_request,
        mock_logger,
    ):
        mock_request.json.return_value = {"success": False}
        payload = {
            "name": "ci",
            "ip": "127.203.121.13",
        }
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(self.access_token)}")
        response = self.client.post("/locations/", data=payload)
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(
            response.json(),
            {"detail": "Service temporarily unavailable, try again later."},
        )
        mock_request.reset_mock()
        mock_request.status_code = status.HTTP_504_GATEWAY_TIMEOUT

        response = self.client.post("/locations/", data=payload)

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(
            response.json(),
            {"detail": "Service temporarily unavailable, try again later."},
        )
        self.assertEqual(mock_logger.call_count, 2)

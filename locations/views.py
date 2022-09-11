from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Location
from .serializers import LocationSerializer


class LocationViewSet(viewsets.ModelViewSet):
    serializer_class = LocationSerializer
    queryset = Location.objects.all()
    permission_classes = (IsAuthenticated,)

    def get_serializer(self, *args, **kwargs):
        if self.request.method == "POST":
            return super().get_serializer(
                *args, fields=["id", "name", "ip", "domain"], **kwargs
            )
        return super().get_serializer(*args, **kwargs)

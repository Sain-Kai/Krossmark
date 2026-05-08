from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import Device

class DeviceKeyAuthentication(BaseAuthentication):
    """
    Accepts either:
    - X-Device-Key: <api_key>
    - Authorization: Device <api_key>
    """
    keyword = "Device"

    def authenticate(self, request):
        key = request.headers.get("X-Device-Key")
        auth = request.headers.get("Authorization", "")

        if not key and auth.startswith(f"{self.keyword} "):
            key = auth.split(" ", 1)[1].strip()

        if not key:
            return None

        try:
            device = Device.objects.get(api_key=key, is_active=True)
        except Device.DoesNotExist:
            raise AuthenticationFailed("Invalid device key")

        return (device, None)

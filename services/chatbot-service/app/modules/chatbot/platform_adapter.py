import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class PlatformAdapter:

    @staticmethod
    async def _get(base_url: str, path: str, token: str) -> dict:
        """Calls an external microservice with the user's JWT — preserves auth context."""
        url = f"{base_url}{path}"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0,
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.warning("HTTP GET request failed for URL %s: %s", url, e)
            return {
                "error": f"Failed to retrieve data from microservice: {str(e)}"
            }

    @staticmethod
    async def get_donor_profile(token: str) -> dict:
        return await PlatformAdapter._get(
            settings.CORE_SERVICE_URL, "/api/v1/donors/me", token
        )

    @staticmethod
    async def get_patient_profile(token: str) -> dict:
        return await PlatformAdapter._get(
            settings.CORE_SERVICE_URL, "/api/v1/patients/me", token
        )

    @staticmethod
    async def get_my_requests(token: str) -> dict:
        return await PlatformAdapter._get(
            settings.CORE_SERVICE_URL, "/api/v1/requests/mine", token
        )

    @staticmethod
    async def get_donor_leaderboard(token: str) -> dict:
        return await PlatformAdapter._get(
            settings.CORE_SERVICE_URL, "/api/v1/leaderboard", token
        )

    @staticmethod
    async def get_notifications(token: str) -> dict:
        return await PlatformAdapter._get(
            settings.NOTIFICATION_SERVICE_URL, "/api/v1/notifications", token
        )

    @staticmethod
    async def get_inventory(token: str) -> dict:
        return await PlatformAdapter._get(
            settings.CORE_SERVICE_URL, "/api/v1/blood-bank/inventory", token
        )

    @staticmethod
    async def get_nearest_blood_banks(token: str) -> dict:
        return await PlatformAdapter._get(
            settings.CORE_SERVICE_URL, "/api/v1/blood-bank/nearest", token
        )

    @staticmethod
    async def get_validation_reports(token: str) -> dict:
        return await PlatformAdapter._get(
            settings.CORE_SERVICE_URL,
            "/api/v1/donors/me/validation-reports",
            token,
        )

    @staticmethod
    async def get_dashboard(token: str) -> dict:
        return await PlatformAdapter._get(
            settings.CORE_SERVICE_URL, "/api/v1/coordinator/dashboard", token
        )

    @staticmethod
    async def get_active_requests(token: str) -> dict:
        return await PlatformAdapter._get(
            settings.CORE_SERVICE_URL,
            "/api/v1/coordinator/requests/active",
            token,
        )

class PlatformService:

    @staticmethod
    def handle_query(query: str):

        query = query.lower()

        if "donor" in query:
            return {
                "status": "success",
                "data": "Donor service not connected yet."
            }

        if "patient" in query:
            return {
                "status": "success",
                "data": "Patient service not connected yet."
            }

        if "blood request" in query:
            return {
                "status": "success",
                "data": "Blood request service not connected yet."
            }

        return {
            "status": "success",
            "data": "Platform information unavailable."
        }
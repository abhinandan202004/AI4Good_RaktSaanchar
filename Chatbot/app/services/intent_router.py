class IntentRouter:

    @staticmethod
    def get_intent(query: str):

        query = query.lower()

        platform_keywords = [
            "my",
            "request",
            "profile",
            "donor",
            "patient",
            "inventory",
            "blood bank",
            "availability",
            "history"
        ]

        knowledge_keywords = [
            "thalassemia",
            "blood donation",
            "blood group",
            "compatibility",
            "eligibility"
        ]

        if any(k in query for k in platform_keywords):
            return "PLATFORM"

        if any(k in query for k in knowledge_keywords):
            return "RAG"

        return "GENERAL"
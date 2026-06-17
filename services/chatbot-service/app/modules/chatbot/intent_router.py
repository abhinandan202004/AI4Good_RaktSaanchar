class IntentRouter:

    @staticmethod
    def get_intent(query: str):

        query = query.lower()

        # Check if the user is asking about their own profile details (blood type/group, profile, identity)
        if any(term in query for term in ["my blood type", "my blood group", "what is my blood", "what's my blood", "my profile", "about me", "who am i", "my details"]):
            return {
                "intent": "PLATFORM",
                "action": "MY_PROFILE"
            }

        # -------------------
        # DONOR
        # -------------------

        if "leaderboard" in query:
            return {
                "intent": "PLATFORM",
                "action": "DONOR_LEADERBOARD"
            }

        if "donor profile" in query or "my donor profile" in query:
            return {
                "intent": "PLATFORM",
                "action": "DONOR_PROFILE"
            }

        if "validation report" in query:
            return {
                "intent": "PLATFORM",
                "action": "VALIDATION_REPORTS"
            }

        if "availability" in query:
            return {
                "intent": "PLATFORM",
                "action": "DONOR_AVAILABILITY"
            }

        # -------------------
        # PATIENT
        # -------------------

        if "patient profile" in query:
            return {
                "intent": "PLATFORM",
                "action": "PATIENT_PROFILE"
            }

        # -------------------
        # REQUESTS
        # -------------------

        if (
            "my requests" in query
            or "blood requests" in query
            or "request history" in query
        ):
            return {
                "intent": "PLATFORM",
                "action": "MY_REQUESTS"
            }

        if "request status" in query:
            return {
                "intent": "PLATFORM",
                "action": "REQUEST_STATUS"
            }

        # -------------------
        # NOTIFICATIONS
        # -------------------

        if "notification" in query:
            return {
                "intent": "PLATFORM",
                "action": "NOTIFICATIONS"
            }

        # -------------------
        # BLOOD BANK
        # -------------------

        if "inventory" in query:
            return {
                "intent": "PLATFORM",
                "action": "INVENTORY"
            }

        if (
            "nearest blood bank" in query
            or "blood bank near me" in query
        ):
            return {
                "intent": "PLATFORM",
                "action": "NEAREST_BLOOD_BANK"
            }

        # -------------------
        # COORDINATOR
        # -------------------

        if "dashboard" in query:
            return {
                "intent": "PLATFORM",
                "action": "DASHBOARD"
            }

        if "active requests" in query:
            return {
                "intent": "PLATFORM",
                "action": "ACTIVE_REQUESTS"
            }

        # -------------------
        # RAG KNOWLEDGE
        # -------------------

        knowledge_keywords = [
            "thalassemia",
            "blood donation",
            "blood group",
            "compatibility",
            "eligibility",
            "donor eligibility",
            "transfusion",
            "blood bank process",
            "faq"
        ]

        if any(word in query for word in knowledge_keywords):
            return {
                "intent": "RAG",
                "action": None
            }

        # -------------------
        # GENERAL CHAT
        # -------------------

        return {
            "intent": "GENERAL",
            "action": None
        }

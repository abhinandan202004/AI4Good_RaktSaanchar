import os
from mistralai import Mistral
import logging

logger = logging.getLogger(__name__)

_client = None

def get_mistral_client():
    global _client
    if _client is not None:
        return _client
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        return None
    try:
        _client = Mistral(api_key=api_key)
    except Exception as e:
        logger.warning("Failed to initialize Mistral client: %s", e)
        _client = None
    return _client


def generate_response(user_message: str) -> str:
    """
    Generate chatbot response using Mistral AI
    """
    client = get_mistral_client()
    if not client:
        logger.warning("Mistral client not initialized. Falling back to simple echo.")
        return "RaktaSanchaar AI Assistant is currently running in fallback mode. Here is a default response to your query: " + user_message

    try:
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[
                {
                    "role": "system",
                    "content": """
                    You are RaktaSanchaar AI Assistant.

                    You help:
                    - Blood Donors
                    - Patients
                    - Blood Banks
                    - Coordinators

                    Answer questions related to:
                    - Blood Donation
                    - Thalassemia
                    - Blood Compatibility
                    - Patient Support
                    - Donor Guidance

                    Keep responses concise and helpful.
                    """
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        )

        return response.choices[0].message.content

    except Exception as e:
        logger.error("Error generating response from Mistral: %s", e)
        return f"Error generating response: {str(e)}"

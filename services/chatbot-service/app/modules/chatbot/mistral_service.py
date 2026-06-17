import os
try:
    from mistralai import Mistral
except ImportError:
    from mistralai.client import Mistral
import logging

logger = logging.getLogger(__name__)

_client = None

def get_mistral_client():
    global _client
    if _client is not None:
        return _client
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key or api_key.startswith("mock-"):
        return None
    try:
        _client = Mistral(api_key=api_key)
    except Exception as e:
        logger.warning("Failed to initialize Mistral client: %s", e)
        _client = None
    return _client


def _get_mock_response(user_message: str) -> str:
    """Provides a smart, rule-based fallback response for common queries when Mistral API key is not configured."""
    msg = user_message.lower().strip()
    
    # 1. Greetings
    if any(greet in msg for greet in ["hello", "hi", "hey", "namaste", "salamat"]):
        return (
            "Namaste! I am your RaktaSanchaar AI Assistant (running in local helper mode).\n\n"
            "How can I help you today? You can ask me about:\n"
            "• Blood group compatibility (e.g., 'who can O- donate to?')\n"
            "• Thalassemia transfusion schedule\n"
            "• RaktSaanchar platform features"
        )
        
    # 2. Compatibility Queries
    if "compatib" in msg or "who can donate" in msg or "who can receive" in msg or "blood group" in msg or "universal" in msg:
        return (
            "🩸 **Blood Group Compatibility Quick Guide:**\n\n"
            "• **O- (O Negative):** Universal Donor. Can donate to all blood types but can only receive from O-.\n"
            "• **AB+ (AB Positive):** Universal Recipient. Can receive from all blood types but can only donate to AB+.\n"
            "• **General Rule:** Positive (+) types can receive from both (+) and (-) of their type, but Negative (-) types can only receive from (-)."
        )
        
    # 3. Thalassemia Queries
    if "thalassemia" in msg or "transfusion" in msg or "schedule" in msg:
        return (
            "🩺 **Thalassemia Transfusion Schedule Info:**\n\n"
            "• Patients with Thalassemia Major generally require regular blood transfusions every **2 to 4 weeks** to maintain healthy hemoglobin levels (typically targeted between 9.5 and 10.5 g/dL).\n"
            "• Through RaktSaanchar, coordinators schedule these transfusions, and you can view your upcoming schedule on your profile dashboard."
        )

    # 4. Profile/Dashboard Queries
    if "profile" in msg or "dashboard" in msg or "points" in msg or "badge" in msg:
        return (
            "👤 **RaktSaanchar Platform Profile & Leaderboard:**\n\n"
            "• **Donors:** You earn points and unlock badges (like Bronze, Silver, Gold, Platinum) for every successful donation and prompt request acceptance. You can check your rank on the Leaderboard!\n"
            "• **Patients:** You can create and track blood requests, and coordinate with matched donors directly."
        )

    # 5. Generic fallback
    return (
        f"Thank you for your question: \"{user_message}\"\n\n"
        "I am currently running in Local Helper Mode (no Mistral API key is configured). "
        "For specific medical inquiries or matching, please coordinate with your dashboard coordinator or visit the nearest blood bank."
    )


def generate_response(user_message: str) -> str:
    """
    Generate chatbot response using Mistral AI or fallback mock helper
    """
    client = get_mistral_client()
    if not client:
        logger.info("Mistral client not configured. Using rule-based local helper.")
        return _get_mock_response(user_message)

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

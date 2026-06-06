import os
from sarvamai import SarvamAI
import logging

logger = logging.getLogger(__name__)

_client = None

def get_sarvam_client():
    global _client
    if _client is not None:
        return _client
    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        return None
    try:
        _client = SarvamAI(api_subscription_key=api_key)
    except Exception as e:
        logger.warning("Failed to initialize SarvamAI client: %s", e)
        _client = None
    return _client

class TranslationService:

    @staticmethod
    def translate_to_english(text: str):
        client = get_sarvam_client()
        if not client:
            return {"translated_text": text, "source_language": "en-IN"}
        try:
            response = client.text.translate(
                input=text,
                source_language_code="auto",
                target_language_code="en-IN"
            )
            return {
                "translated_text": response.translated_text,
                "source_language": response.source_language_code
            }
        except Exception as e:
            logger.warning("Sarvam AI translation error: %s", e)
            return {"translated_text": text, "source_language": "en-IN"}

    @staticmethod
    def translate_from_english(text: str, target_language: str):
        if target_language in ["en-IN", "en"]:
            return text
        client = get_sarvam_client()
        if not client:
            return text
        try:
            response = client.text.translate(
                input=text,
                source_language_code="en-IN",
                target_language_code=target_language
            )
            return response.translated_text
        except Exception as e:
            logger.warning("Sarvam AI reverse translation error: %s", e)
            return text

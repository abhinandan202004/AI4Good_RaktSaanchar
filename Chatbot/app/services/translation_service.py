import os

from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()

client = SarvamAI(
    api_subscription_key=os.getenv("SARVAM_API_KEY")
)


class TranslationService:

    @staticmethod
    def translate_to_english(text: str):

        response = client.text.translate(
            input=text,
            source_language_code="auto",
            target_language_code="en-IN"
        )

        return {
            "translated_text": response.translated_text,
            "source_language": response.source_language_code
        }

    @staticmethod
    def translate_from_english(
        text: str,
        target_language: str
    ):

        # No translation needed
        if target_language in ["en-IN", "en"]:
            return text

        response = client.text.translate(
            input=text,
            source_language_code="en-IN",
            target_language_code=target_language
        )

        return response.translated_text
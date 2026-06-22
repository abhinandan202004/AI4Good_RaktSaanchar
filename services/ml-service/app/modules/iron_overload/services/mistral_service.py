import logging

try:
    from mistralai import Mistral
except ImportError:
    from mistralai.client import Mistral

from app.core.config import settings

logger = logging.getLogger(__name__)


class MistralService:

    @staticmethod
    def generate_response(prompt: str) -> str:
        # Use settings (loaded from HF Space secrets / .env) rather than bare os.getenv
        api_key = settings.MISTRAL_API_KEY
        if not api_key or api_key.startswith("mock-"):
            logger.warning(
                "MISTRAL_API_KEY is not set on this deployment. "
                "Add it as a Hugging Face Space secret to enable real AI explanations."
            )
            return (
                "🤖 [Local Helper Mode - Mock AI Explanation]\n\n"
                "Based on the analysis, here is the interpretation of your MRI report:\n"
                "• **Current Condition & Severity**: Your risk is assessed as shown in the report. "
                "The liver iron concentration and T2* values indicate your current iron overload levels.\n"
                "• **Risk Prediction**: Our model predicts the future risk progression as detailed. "
                "Please coordinate with your thalassemia care coordinator to adjust your chelation therapy if needed.\n"
                "• **Disclaimer**: This is a mock AI response since a live Mistral API key is not configured. "
                "Please consult with your doctor for actual clinical decisions."
            )

        try:
            client = Mistral(api_key=api_key)
            response = client.chat.complete(
                model="mistral-small-latest",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("Mistral API call failed: %s", e)
            return f"[Error generating response from Mistral AI: {str(e)}]"

import os
try:
    from mistralai import Mistral
except ImportError:
    from mistralai.client import Mistral


class MistralService:

    @staticmethod
    def generate_response(prompt: str):
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key or api_key.startswith("mock-"):
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
            return f"[Error generating response from Mistral AI: {str(e)}]"


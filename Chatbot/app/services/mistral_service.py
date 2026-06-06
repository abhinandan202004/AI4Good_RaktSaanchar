import os
from dotenv import load_dotenv
from mistralai import Mistral

# Load environment variables
load_dotenv()

# Get API Key
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

if not MISTRAL_API_KEY:
    raise ValueError("MISTRAL_API_KEY not found in .env file")

# Initialize Client
client = Mistral(api_key=MISTRAL_API_KEY)


def generate_response(user_message: str) -> str:
    """
    Generate chatbot response using Mistral AI
    """

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
        return f"Error generating response: {str(e)}"
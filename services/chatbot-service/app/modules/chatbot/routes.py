from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.dependencies import get_db, get_current_user
from app.modules.chatbot.translation_service import TranslationService
from app.modules.chatbot.intent_router import IntentRouter
from app.modules.chatbot.rag_service import rag_service
from app.modules.chatbot.mistral_service import generate_response
from app.modules.chatbot.platform_adapter import PlatformAdapter

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    user_message: str
    detected_language: str
    intent: str
    action: str | None = None
    response: str


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db=Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Step 1: Translate user message to English
    translated = TranslationService.translate_to_english(request.message)

    english_message = translated["translated_text"]
    source_language = translated["source_language"]

    # Step 2: Detect intent and action
    route = IntentRouter.get_intent(english_message)

    intent = route["intent"]
    action = route["action"]

    # Step 3: Route request
    if intent == "PLATFORM":
        token = current_user.token
        if action == "MY_PROFILE":
            user_profile = await PlatformAdapter.get_user_profile(token)
            if current_user.role == "patient":
                profile_data = await PlatformAdapter.get_patient_profile(token)
            else:
                profile_data = await PlatformAdapter.get_donor_profile(token)
            data = {
                "user": user_profile,
                "profile": profile_data
            }
        elif action == "DONOR_PROFILE":
            data = await PlatformAdapter.get_donor_profile(token)
        elif action == "PATIENT_PROFILE":
            data = await PlatformAdapter.get_patient_profile(token)
        elif action == "MY_REQUESTS":
            data = await PlatformAdapter.get_my_requests(token)
        elif action == "DONOR_LEADERBOARD":
            data = await PlatformAdapter.get_donor_leaderboard(token)
        elif action == "VALIDATION_REPORTS":
            data = await PlatformAdapter.get_validation_reports(token)
        elif action == "NOTIFICATIONS":
            data = await PlatformAdapter.get_notifications(token)
        elif action == "INVENTORY":
            data = await PlatformAdapter.get_inventory(token)
        elif action == "NEAREST_BLOOD_BANK":
            data = await PlatformAdapter.get_nearest_blood_banks(token)
        elif action == "DASHBOARD":
            data = await PlatformAdapter.get_dashboard(token)
        elif action == "ACTIVE_REQUESTS":
            data = await PlatformAdapter.get_active_requests(token)
        else:
            data = {"message": "Action not implemented."}

        # Let Mistral format backend response naturally
        llm_response = generate_response(
            f"""
            User Question:
            {english_message}

            Backend Data:
            {data}

            Answer the user naturally based ONLY on the Backend Data. 
            If the backend data contains an error (e.g. 'not found') or is empty, tell the user gracefully.
            Do not invent or hallucinate data.
            """
        )

    elif intent == "RAG":
        llm_response = rag_service.get_response(english_message)

    else:
        llm_response = generate_response(english_message)

    # Step 4: Translate response back to user's language
    final_response = TranslationService.translate_from_english(
        llm_response, source_language
    )

    return {
        "user_message": request.message,
        "detected_language": source_language,
        "intent": intent,
        "action": action,
        "response": final_response,
    }

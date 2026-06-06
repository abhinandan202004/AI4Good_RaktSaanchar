from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.dependencies import get_db, get_current_user
from app.modules.chatbot.translation_service import TranslationService
from app.modules.chatbot.intent_router import IntentRouter
from app.modules.chatbot.rag_service import rag_service
from app.modules.chatbot.mistral_service import generate_response
from app.modules.chatbot.platform_adapter import PlatformAdapter

router = APIRouter(
    prefix="/chat",
    tags=["Chatbot"]
)


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
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # Step 1: Translate user message to English
    translated = TranslationService.translate_to_english(
        request.message
    )

    english_message = translated["translated_text"]
    source_language = translated["source_language"]

    # Step 2: Detect intent and action
    route = IntentRouter.get_intent(
        english_message
    )

    intent = route["intent"]
    action = route["action"]

    # Step 3: Route request
    if intent == "PLATFORM":
        if action == "DONOR_PROFILE":
            data = PlatformAdapter.get_donor_profile(db, current_user.id)
        elif action == "PATIENT_PROFILE":
            data = PlatformAdapter.get_patient_profile(db, current_user.id)
        elif action == "MY_REQUESTS":
            data = PlatformAdapter.get_my_requests(db, current_user.id)
        elif action == "DONOR_LEADERBOARD":
            data = PlatformAdapter.get_donor_leaderboard(db)
        elif action == "VALIDATION_REPORTS":
            data = PlatformAdapter.get_validation_reports(db, current_user.id)
        elif action == "NOTIFICATIONS":
            data = PlatformAdapter.get_notifications(db, current_user.id)
        elif action == "INVENTORY":
            data = PlatformAdapter.get_inventory(db, current_user.id, current_user.role)
        elif action == "NEAREST_BLOOD_BANK":
            data = PlatformAdapter.get_nearest_blood_banks(db, current_user.id)
        elif action == "DASHBOARD":
            data = PlatformAdapter.get_dashboard(db)
        elif action == "ACTIVE_REQUESTS":
            data = PlatformAdapter.get_active_requests(db)
        else:
            data = {"message": "Action not implemented."}

        # Let Mistral format backend response naturally
        llm_response = generate_response(
            f"""
            User Question:
            {english_message}

            Backend Data:
            {data}

            Answer the user naturally.
            """
        )

    elif intent == "RAG":
        llm_response = rag_service.get_response(
            english_message
        )

    else:
        llm_response = generate_response(
            english_message
        )

    # Step 4: Translate response back to user's language
    final_response = TranslationService.translate_from_english(
        llm_response,
        source_language
    )

    return {
        "user_message": request.message,
        "detected_language": source_language,
        "intent": intent,
        "action": action,
        "response": final_response
    }

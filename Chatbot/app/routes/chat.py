from fastapi import APIRouter
from pydantic import BaseModel

from app.services.translation_service import TranslationService
from app.services.intent_router import IntentRouter
from app.services.rag_service import rag_service
from app.services.mistral_service import generate_response
from app.services.platform_service import PlatformService

router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    user_message: str
    detected_language: str
    intent: str
    response: str


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):

    # Step 1: Translate user message to English
    translated = TranslationService.translate_to_english(
        request.message
    )

    english_message = translated["translated_text"]
    source_language = translated["source_language"]

    # Step 2: Detect intent
    intent = IntentRouter.get_intent(
        english_message
    )

    # Step 3: Route request
    if intent == "PLATFORM":

        platform_result = PlatformService.handle_query(
            english_message
        )

        llm_response = platform_result["data"]

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
        "response": final_response
    }
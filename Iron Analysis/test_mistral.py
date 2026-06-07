from services.mistral_service import MistralService

response = MistralService.generate_response(
    "Say hello in one sentence."
)

print(response)
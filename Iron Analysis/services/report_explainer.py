from services.mistral_service import (
    MistralService
)


class ReportExplainer:

    @staticmethod
    def explain(
        extracted_values: dict,
        current_risk: str,
        risk_score: int,
        days_until_high_risk: int
    ):

        prompt = f"""
You are an expert thalassemia care assistant.

MRI Analysis:

Heart T2*: {extracted_values.get('heart_t2_star_ms')}

Liver T2*: {extracted_values.get('liver_t2_star_ms')}

Liver Iron Concentration:
{extracted_values.get('liver_iron_concentration_mg_g')} mg/g

Ferritin:
{extracted_values.get('serum_ferritin')}

Current Risk:
{current_risk}

Risk Score:
{risk_score}/100

Predicted Days Until High Risk:
{days_until_high_risk}

Explain:
1. Current condition
2. Iron overload severity
3. Future risk
4. Recommendations

Keep response patient friendly.
"""

        return MistralService.generate_response(
            prompt
        )
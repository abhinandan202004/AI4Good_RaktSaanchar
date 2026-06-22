from app.modules.iron_overload.parser.pdf_parser import PDFParser
from app.modules.iron_overload.parser.image_parser import ImageParser
from app.modules.iron_overload.parser.text_parser import TextParser

from app.modules.iron_overload.risk_engine.current_risk import CurrentRiskEngine
from app.modules.iron_overload.predictor.predictor import IronOverloadPredictor

from app.modules.iron_overload.services.report_explainer import ReportExplainer


class IronOverloadService:

    @staticmethod
    def analyze_text(text: str, api_key: str | None = None):
        report_data = TextParser.parse(text)
        return IronOverloadService._process(report_data, api_key=api_key)

    @staticmethod
    def analyze_pdf(file_path: str, api_key: str | None = None):
        report_data = PDFParser.parse(file_path)
        return IronOverloadService._process(report_data, api_key=api_key)

    @staticmethod
    def analyze_image(file_path: str, api_key: str | None = None):
        report_data = ImageParser.parse(file_path)
        return IronOverloadService._process(report_data, api_key=api_key)

    @staticmethod
    def _process(report_data: dict, api_key: str | None = None):

        risk_result = CurrentRiskEngine.calculate_risk(
            heart_t2_star_ms=report_data.get(
                "heart_t2_star_ms"
            ),
            liver_iron_concentration_mg_g=report_data.get(
                "liver_iron_concentration_mg_g"
            ),
            serum_ferritin=report_data.get(
                "serum_ferritin"
            )
        )

        prediction = IronOverloadPredictor.predict(
            report_data
        )

        try:
            explanation = ReportExplainer.explain(
                extracted_values=report_data,
                current_risk=risk_result["current_risk"],
                risk_score=risk_result["risk_score"],
                days_until_high_risk=prediction[
                    "days_until_high_risk"
                ],
                api_key=api_key
            )
        except Exception:
            explanation = (
                "Unable to generate AI explanation."
            )

        return {
            "extracted_values": report_data,
            "current_risk": risk_result["current_risk"],
            "risk_score": risk_result["risk_score"] / 100.0,
            "days_until_high_risk": prediction[
                "days_until_high_risk"
            ],
            "explanation": explanation
        }


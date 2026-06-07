from pydantic import BaseModel


class MRIReportData(BaseModel):
    heart_t2_star_ms: float | None = None
    liver_t2_star_ms: float | None = None
    liver_iron_concentration_mg_g: float | None = None
    serum_ferritin: float | None = None

    transfusions_last_12_months: int | None = None
    lifetime_transfusions: int | None = None

    chelation_adherence: str | None = None
    chelation_therapy: str | None = None

    age: int | None = None
    weight_kg: float | None = None
    hemoglobin: float | None = None
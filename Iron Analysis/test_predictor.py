from predictor.predictor import IronOverloadPredictor

sample = {
    "age": 18,
    "weight_kg": 45,
    "hemoglobin": 8.5,
    "serum_ferritin": 3200,
    "heart_t2_star_ms": 12,
    "liver_t2_star_ms": 5,
    "liver_iron_concentration_mg_g": 8,
    "transfusions_last_12_months": 18,
    "lifetime_transfusions": 120
}

result = IronOverloadPredictor.predict(sample)

print(result)
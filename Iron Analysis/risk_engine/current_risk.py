class CurrentRiskEngine:

    @staticmethod
    def calculate_risk(
        heart_t2_star_ms: float | None,
        liver_iron_concentration_mg_g: float | None,
        serum_ferritin: float | None = None
    ):

        score = 0

        # Heart T2*
        if heart_t2_star_ms is not None:

            if heart_t2_star_ms < 6:
                score += 40

            elif heart_t2_star_ms < 10:
                score += 30

            elif heart_t2_star_ms < 20:
                score += 15

        # Liver Iron Concentration
        if liver_iron_concentration_mg_g is not None:

            if liver_iron_concentration_mg_g > 15:
                score += 40

            elif liver_iron_concentration_mg_g > 7:
                score += 30

            elif liver_iron_concentration_mg_g > 3:
                score += 15

        # Ferritin
        if serum_ferritin is not None:

            if serum_ferritin > 5000:
                score += 20

            elif serum_ferritin > 2500:
                score += 15

            elif serum_ferritin > 1000:
                score += 10

        score = min(score, 100)

        # Risk Category
        if score >= 80:
            risk = "Critical"

        elif score >= 60:
            risk = "High"

        elif score >= 30:
            risk = "Moderate"

        else:
            risk = "Low"

        return {
            "risk_score": score,
            "current_risk": risk
        }
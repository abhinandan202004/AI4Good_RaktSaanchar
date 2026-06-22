import re


class MRIValueExtractor:

    @staticmethod
    def extract(text: str) -> dict:
        """
        Extract MRI iron overload values from free-form report text.
        Patterns cover: standard labels, abbreviations (LIC, T2*), various
        separators (: / = / space), optional units (ms, mg/g, ng/mL, ug/L).
        """
        data = {}

        patterns = {
            # Heart T2* — e.g. "Heart T2*: 18.4 ms", "Cardiac T2* 20ms",
            # "T2* (heart): 15", "myocardial T2* = 12.3"
            "heart_t2_star_ms": [
                r"(?:heart|cardiac|myocardial)\s*t2\*?\s*(?:\(ms\))?\s*[:\-=]?\s*(\d+\.?\d*)\s*(?:ms)?",
                r"t2\*?\s*(?:\(heart\)|heart)\s*[:\-=]?\s*(\d+\.?\d*)\s*(?:ms)?",
                r"heart\s*t2\s*star\s*[:\-=]?\s*(\d+\.?\d*)\s*(?:ms)?",
            ],

            # Liver T2* — e.g. "Liver T2*: 7.2 ms", "hepatic T2* 9 ms"
            "liver_t2_star_ms": [
                r"(?:liver|hepatic)\s*t2\*?\s*(?:\(ms\))?\s*[:\-=]?\s*(\d+\.?\d*)\s*(?:ms)?",
                r"t2\*?\s*(?:\(liver\)|liver)\s*[:\-=]?\s*(\d+\.?\d*)\s*(?:ms)?",
                r"liver\s*t2\s*star\s*[:\-=]?\s*(\d+\.?\d*)\s*(?:ms)?",
            ],

            # Liver Iron Concentration — e.g. "LIC: 4.2 mg/g", "liver iron: 5",
            # "liver iron concentration 3.8 mg Fe/g dw", "hepatic iron 6.1"
            "liver_iron_concentration_mg_g": [
                r"\blic\b\s*[:\-=]?\s*(\d+\.?\d*)\s*(?:mg[\/\s]?(?:fe[\/\s]?)?g)?",
                r"liver\s*iron\s*concentration\s*[:\-=]?\s*(\d+\.?\d*)",
                r"liver\s*iron\s*[:\-=]?\s*(\d+\.?\d*)\s*(?:mg[\/\s]?(?:fe[\/\s]?)?g)?",
                r"hepatic\s*iron\s*(?:concentration\s*)?[:\-=]?\s*(\d+\.?\d*)",
                r"iron\s*concentration\s*[:\-=]?\s*(\d+\.?\d*)",
            ],

            # Serum Ferritin — e.g. "Ferritin: 1250", "serum ferritin = 3400 ng/mL",
            # "S.Ferritin 2800", "ferritin level: 1500 ug/L"
            "serum_ferritin": [
                r"(?:serum\s+)?ferritin\s*(?:level)?\s*[:\-=]?\s*(\d+\.?\d*)\s*(?:ng[\/\s]?ml|ug[\/\s]?l)?",
                r"s\.?\s*ferritin\s*[:\-=]?\s*(\d+\.?\d*)",
                r"ferritin\s*[:\-=]\s*(\d+\.?\d*)",
            ],
        }

        for field, regex_list in patterns.items():
            for regex in regex_list:
                match = re.search(
                    regex,
                    text,
                    re.IGNORECASE | re.DOTALL
                )
                if match:
                    data[field] = float(match.group(1))
                    break

        return data

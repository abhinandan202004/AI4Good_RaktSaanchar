import re


class MRIValueExtractor:

    @staticmethod
    def extract(text: str):

        data = {}

        patterns = {
            "heart_t2_star_ms": [
                r"heart\s*t2\*?\s*[:\-]?\s*(\d+\.?\d*)"
            ],

            "liver_t2_star_ms": [
                r"liver\s*t2\*?\s*[:\-]?\s*(\d+\.?\d*)"
            ],

            "liver_iron_concentration_mg_g": [
                r"liver\s*iron\s*concentration.*?(\d+\.?\d*)",
                r"lic.*?(\d+\.?\d*)"
            ],

            "serum_ferritin": [
                r"ferritin.*?(\d+\.?\d*)"
            ]
        }

        for field, regex_list in patterns.items():

            for regex in regex_list:

                match = re.search(
                    regex,
                    text,
                    re.IGNORECASE | re.DOTALL
                )

                if match:

                    data[field] = float(
                        match.group(1)
                    )

                    break

        return data
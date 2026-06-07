from services.iron_overload_service import (
    IronOverloadService
)

sample_report = """
Heart T2*: 14.5 ms

Liver T2*: 5.2 ms

Liver Iron Concentration: 8.3 mg/g

Ferritin: 2500
"""

result = (
    IronOverloadService.analyze_text(
        sample_report
    )
)

print(result)
from parser import TextParser

sample_text = """
Heart T2*: 14.5 ms

Liver T2*: 5.2 ms

Liver Iron Concentration:
8.3 mg/g dry weight

Ferritin: 2450
"""

result = TextParser.parse(
    sample_text
)

print(result)
from app.modules.iron_overload.parser.extractor import MRIValueExtractor


class TextParser:

    @staticmethod
    def parse(text: str):

        return MRIValueExtractor.extract(
            text
        )

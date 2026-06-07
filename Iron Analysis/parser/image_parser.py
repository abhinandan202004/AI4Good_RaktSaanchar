import easyocr

from parser.extractor import MRIValueExtractor


class ImageParser:

    reader = easyocr.Reader(
        ['en']
    )

    @classmethod
    def parse(
        cls,
        file_path: str
    ):

        result = cls.reader.readtext(
            file_path,
            detail=0
        )

        text = " ".join(result)

        return MRIValueExtractor.extract(
            text
        )
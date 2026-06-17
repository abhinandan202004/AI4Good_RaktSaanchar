import easyocr

from app.modules.iron_overload.parser.extractor import MRIValueExtractor


class ImageParser:

    reader = None

    @classmethod
    def get_reader(cls):
        if cls.reader is None:
            cls.reader = easyocr.Reader(['en'])
        return cls.reader

    @classmethod
    def parse(
        cls,
        file_path: str
    ):
        reader = cls.get_reader()
        result = reader.readtext(
            file_path,
            detail=0
        )

        text = " ".join(result)

        return MRIValueExtractor.extract(
            text
        )

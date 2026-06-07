import fitz

from parser.extractor import MRIValueExtractor


class PDFParser:

    @staticmethod
    def parse(file_path: str):

        text = ""

        document = fitz.open(
            file_path
        )

        for page in document:

            text += page.get_text()

        document.close()

        return MRIValueExtractor.extract(
            text
        )
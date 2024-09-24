from nomad.config.models.plugins import ParserEntryPoint
from pydantic import Field


class NewParserEntryPoint(ParserEntryPoint):
    parameter: int = Field(0, description='Custom configuration parameter')

    def load(self):
        from nomad_parser_yambospectra.parsers.parser import YAMBOSpectraParser

        return YAMBOSpectraParser(**self.dict())


parser_entry_point = NewParserEntryPoint(
    name='YAMBOSpectraParser',
    description='YAMBOSpectraParser entry point configuration.',
    # mainfile_name_re='.*\.newmainfilename',
    mainfile_contents_re='http://www.yambo-code.org',
)

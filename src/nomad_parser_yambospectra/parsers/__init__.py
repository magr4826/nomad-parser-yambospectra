from nomad.config.models.plugins import ParserEntryPoint
from pydantic import Field


class NewParserEntryPoint(ParserEntryPoint):
    parameter: int = Field(0, description='Custom configuration parameter')

    def load(self):
        from nomad_parser_yambospectra.parsers.parser import YAMBO_SpectraParser

        return YAMBO_SpectraParser(**self.dict())


parser_entry_point = NewParserEntryPoint(
    name='YAMBO_SpectraParser',
    description='YAMBO_SpectraParser entry point configuration.',
    #mainfile_name_re='.*\.newmainfilename',
    mainfile_contents_re='http://www.yambo-code.org',
)

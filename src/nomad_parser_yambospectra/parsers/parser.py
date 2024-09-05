from typing import (
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import (
        EntryArchive,
    )
    from structlog.stdlib import (
        BoundLogger,
    )

from nomad.config import config
from nomad.parsing.parser import MatchingParser
from nomad_simulations.schema_packages.general import Simulation, Program
from nomad.parsing.file_parser import Quantity, TextParser, DataTextParser
from nomad.units import ureg

from nomad_simulations.schema_packages.model_method import ModelMethod, DFT

from nomad_parser_yambospectra.schema_packages.schema_package import RPA_Spectra

from nomad.datamodel.metainfo.workflow import Workflow

configuration = config.get_plugin_entry_point(
    'nomad_parser_yambospectra.parsers:parser_entry_point'
)


class epsilonParser(TextParser):
    def init_quantities(self):
        self._quantities = [
            Quantity("Damping", r"% DmRngeXd\s*\n# \|\s*(\d+\.\d+)\s*\|\s*(\d+\.\d+)"),
            Quantity("EnergyRange", r"% EnRngeXd\s*\n# \|\s*(\d+\.\d+)\s*\|\s*(\d+\.\d+)"),
            Quantity("BandRange", r"% BndsRnXd\s*\n# \|\s*(\d+)\s*\|\s*(\d+)"),
            Quantity("Direction", r"% LongDrXd\s*\n# \|\s*(\d+\.\d+)\s*\|\s*(\d+\.\d+)\s*\|\s*(\d+\.\d+)"),
            Quantity("NumberOfFreqs", r"ETStpsXd=\s*(\d+)"),
            Quantity("FFTVecs", r"FFTGvecs=\s*(\d+)"),
            Quantity("GVec_Cutoff", r"NGsBlkXd=\s*(\d+)"),
        ]

class NewParser(MatchingParser):
    def parse(
        self,
        mainfile: str,
        archive: 'EntryArchive',
        logger: 'BoundLogger',
        child_archives: dict[str, 'EntryArchive'] = None,
    ) -> None:
        simulation = Simulation()
        archive.data = simulation


        program = Program(name="YAMBO")
        simulation.program = program

        my_eps = epsilonParser(mainfile=mainfile)
        my_eps.mainfile = mainfile
        my_eps.logger = logger

        rpa = RPA_Spectra()
        rpa.damping = my_eps.get("Damping") * ureg("eV")
        rpa.energy_range = my_eps.get("EneryRange")
        rpa.band_range = my_eps.get("BandRange")
        rpa.direction = my_eps.get("Direction")
        rpa.numberOfFreqs = my_eps.get("NumberOfFreqs")
        rpa.FFTVecs = my_eps.get("FFTVecs")
        rpa.GVecs = my_eps.get("GVec_Cutoff") * 1e-3* ureg("rydberg")

        output = DataTextParser(mainfile)
        print(output)

        simulation.model_method.append(rpa)

        print(simulation)
        print(simulation.model_method[0].GVecs)

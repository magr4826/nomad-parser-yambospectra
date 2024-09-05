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
from nomad_simulations.schema_packages.numerical_settings import KMesh
from nomad_simulations.schema_packages.variables import Variables, Frequency
from nomad_parser_yambospectra.schema_packages.properties import Permittivity_OneAxis, myOutputs
from nomad.parsing.file_parser import Quantity, TextParser, DataTextParser
from nomad.units import ureg

from nomad_simulations.schema_packages.model_method import ModelMethod, DFT

from nomad_parser_yambospectra.schema_packages.schema_package import RPA_Spectra

from nomad.datamodel.metainfo.workflow import Workflow

import numpy as np
import os

configuration = config.get_plugin_entry_point(
    'nomad_parser_yambospectra.parsers:parser_entry_point'
)


class epsilonInputParser(TextParser):
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

class QEInputParser(TextParser):
    # we really only need the k-points from the input file,
    # as we can get the rest from the output file

    def init_quantities(self):
        self._quantities = [Quantity("kpoints", r"K_POINTS crystal\n\d+\n([\d.\d+\s]*)"),]



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

        # parse the input properties
        my_eps = epsilonInputParser(mainfile=mainfile)
        my_eps.mainfile = mainfile
        my_eps.logger = logger


        # store the input variables in the schema
        rpa = RPA_Spectra()
        rpa.damping = my_eps.get("Damping") * ureg("eV")
        rpa.energy_range = my_eps.get("EneryRange")
        rpa.band_range = my_eps.get("BandRange")
        rpa.direction = my_eps.get("Direction")
        rpa.numberOfFreqs = my_eps.get("NumberOfFreqs")
        rpa.FFTVecs = my_eps.get("FFTVecs")
        rpa.GVecs = my_eps.get("GVec_Cutoff") * 1e-3* ureg("rydberg")
        simulation.model_method.append(rpa)

        # parse the output properties
        output_parsed = DataTextParser(mainfile=mainfile,dtype=np.float32)
        freqs = output_parsed.data[:,0]
        epsI = output_parsed.data[:,1]
        epsR = output_parsed.data[:,2]

        # store the output properties
        freqs_nomad = Frequency(points = freqs * ureg("eV"))

        perm = Permittivity_OneAxis()
        perm.variables.append(freqs_nomad)
        perm.value = (epsR + 1j*epsI).reshape([-1,1,1])
        output = myOutputs()
        output.permittivity_oneaxis.append(perm)
        simulation.outputs.append(output)

        # this concludes the YAMBO part
        # we get the model system and the ground-state parameters from the QE-out-parser

        # as we have low verbosity and no xml file, we can only get the k-points from
        # the input file
        # check if theres a QE input file in the same folder
        all_files = os.listdir()
        QE_input = None
        for filename in all_files:
            if "pw" in filename and "in" in filename:
                QE_input = filename
                break

        if QE_input is not None:
            my_qein = QEInputParser(mainfile=QE_input)
            kmesh = KMesh()
            kmesh.all_points = np.array(my_qein.get("kpoints")).reshape([-1,4])[:,:3]
            print(kmesh.all_points)

        else:
            print("No k-point data!")
        print(simulation)

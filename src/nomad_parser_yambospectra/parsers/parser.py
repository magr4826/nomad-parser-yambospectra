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
from nomad_simulations.schema_packages.model_system import AtomicCell, ModelSystem
from nomad_parser_yambospectra.schema_packages.properties import Permittivity_OneAxis, myOutputs
from nomad.parsing.file_parser import Quantity, TextParser, DataTextParser
from nomad_simulations.schema_packages.atoms_state import AtomsState
from nomad.units import ureg

from nomad_simulations.schema_packages.model_method import ModelMethod, DFT

from nomad_parser_yambospectra.schema_packages.schema_package import RPA_Spectra, RPA_NumSettings

from nomad.datamodel.metainfo.workflow import Workflow

import numpy as np
import os
import glob

configuration = config.get_plugin_entry_point(
    'nomad_parser_yambospectra.parsers:parser_entry_point'
)


def get_files(pattern: str, filepath: str, stripname: str = '', deep: bool = True):
    """Get files following the `pattern` with respect to the file `stripname` (usually this
    being the mainfile of the given parser) up to / down from the `filepath` (`deep=True` going
    down, `deep=False` up)

    Args:
        pattern (str): targeted pattern to be found
        filepath (str): filepath to start the search
        stripname (str, optional): name with respect to which do the search. Defaults to ''.
        deep (bool, optional): boolean setting the path in the folders to scan (down or up). Defaults to down=True.

    Returns:
        list: List of found files.
    """
    for _ in range(10):
        filenames = glob.glob(f'{os.path.dirname(filepath)}/{pattern}')
        pattern = os.path.join('**' if deep else '..', pattern)
        if filenames:
            break

    if len(filenames) > 1:
        # filter files that match
        suffix = os.path.basename(filepath).strip(stripname)
        matches = [f for f in filenames if suffix in f]
        filenames = matches if matches else filenames

    filenames = [f for f in filenames if os.access(f, os.F_OK)]
    return filenames


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
    # we still get some other stuff which is easier to parse here

    def init_quantities(self):
        self._quantities = [Quantity("kpoints", r"K_POINTS crystal\n\d+\n([\d.\d+\s]*)"),
                            Quantity("atom_pos", r' *[A-Za-z]+ +(\d.\d+) (\d.\d+) (\d.\d+)',repeats=True),
                            Quantity("atom_types", r' *([A-Za-z]+) +\d.\d+',repeats=True),]


class QEOutputParser(TextParser):
    # This is a selfbuilt output parser
    def init_quantities(self):
        self._quantities = [Quantity("lattice", r' *a\(\d\) \= \( *([\-\.\d]+) *([\-\.\d]+) *([\-\.\d]+)', repeats = True),
                            Quantity("alat", r"\(alat\)\s*=\s*(\d+.\d+)")]






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
        rpa.energy_range = my_eps.get("EnergyRange")
        rpa.direction = my_eps.get("Direction")
        rpa.numberOfFreqs = my_eps.get("NumberOfFreqs")

        rpa_settings = RPA_NumSettings
        rpa_settings.band_range = my_eps.get("BandRange")
        rpa_settings.FFTVecs = my_eps.get("FFTVecs")
        rpa_settings.GVecs = my_eps.get("GVec_Cutoff") * 1e-3* ureg("rydberg")
        rpa.numerical_settings.append(rpa_settings)
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

        #all_files = glob.glob("*")

        QE_input = get_files("*.in", filepath=mainfile)
        if len(QE_input) == 0:
            print("No QE input file!! Cannot setup ModelSystem & DFT properties.")
            return
        my_qein = QEInputParser(mainfile=QE_input[0])

        QE_output = get_files("*.out", filepath=mainfile)
        if len(QE_output) == 0:
            print("No QE output file!! Cannot setup ModelSystem & DFT properties.")
            return
        my_qeout = QEInputParser(mainfile=QE_output[0])

        kmesh = KMesh()
        kmesh.all_points = np.array(my_qein.get("kpoints")).reshape([-1,4])[:,:3]

        lattice_vecs = np.array(my_qeout.get("lattice"))* my_qeout.get("alat")
        atoms_states = [AtomsState(chemical_symbol=element) for element in my_qein.get("atom_types")]
        atomic_pos_crystal = my_qein.get("atom_pos")
        atomic_pos_cart = np.array([np.matmul(crystal_pos,lattice_vecs) for crystal_pos in atomic_pos_crystal])* ureg("bohr")
        cell = AtomicCell(lattice_vectors = lattice_vecs,atoms_state=atoms_states, positions=atomic_pos_cart)

        modelsys = ModelSystem()
        modelsys.cell.append(cell)
        simulation.model_system.append(modelsys)

        print(simulation)
        print(simulation.model_system)

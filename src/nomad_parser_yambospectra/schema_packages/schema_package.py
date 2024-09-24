import numpy as np
from nomad.config import config
from nomad.metainfo import Quantity, SchemaPackage
from nomad_simulations.schema_packages.model_method import ModelMethod
from nomad_simulations.schema_packages.numerical_settings import NumericalSettings

configuration = config.get_plugin_entry_point(
    'nomad_parser_yambospectra.schema_packages:schema_package_entry_point'
)

m_package = SchemaPackage()


class RPASpectra(ModelMethod):
    """
    A section used to define the basic parameters defining a RPA simulation used to
    calculate spectroscopic properties.
    """

    damping = Quantity(
        type=np.float64,
        unit='joule',
        description='Spectral Broadening',
        shape=[2],
    )

    energy_range = Quantity(
        type=np.float64, unit='joule', description='Energy Range', shape=[2]
    )

    direction = Quantity(
        # ? you can also use strings here (strings are easier to query and work with than multidimensional arrays), but this is fine too
        type=np.int32,
        description='Direction in which the RPAspectra was calculated',
        shape=[3],
    )

    n_frequencies = Quantity(
        type=np.int32,
        description='Number of frequencies on which the spectra was calculated',
    )


# ? maybe `RPASpectraNumericalSettings` is better?
class RPANumericalSettings(NumericalSettings):
    """
    A section used to define the numerical settings used in a RPA calculation.
    """

    # ! I don't think this quantity is necessary, as it seems to be the G cutoff (i.e., part of the DFT part of your workflow, so it should be parsed somewhere else)
    # ! read more: https://www.yambo-code.eu/wiki/index.php/Variables#FFTGvecs
    FFTVecs = Quantity(
        type=np.int32,
        description='FFTGVecs (in Yambo, idk what it actually is)',
    )

    g_vectors_screening = Quantity(
        type=np.float64,
        unit='joule',
        description='Energy cut off in the screening (response block size). This is the `NGsBlkXd` variable in the input file.',
    )

    bands_range = Quantity(
        type=np.int32,
        description='Bands range: number of bands entering in the sum over states in the RPA response function',
        shape=[2],
    )


m_package.__init_metainfo__()

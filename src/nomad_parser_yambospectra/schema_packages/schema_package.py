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

import numpy as np

from nomad.config import config
from nomad.datamodel.data import Schema
from nomad.datamodel.metainfo.annotations import ELNAnnotation, ELNComponentEnum
from nomad.metainfo import Quantity, SchemaPackage
from nomad_simulations.schema_packages.model_method import ModelMethod
from nomad_simulations.schema_packages.numerical_settings import NumericalSettings


configuration = config.get_plugin_entry_point(
    'nomad_parser_yambospectra.schema_packages:schema_package_entry_point'
)

m_package = SchemaPackage()


class NewSchemaPackage(Schema):
    name = Quantity(
        type=str, a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity)
    )
    message = Quantity(type=str)

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        logger.info('NewSchema.normalize', parameter=configuration.parameter)
        self.message = f'Hello {self.name}!'


class RPA_Spectra(ModelMethod):
    damping = Quantity(type = np.float64, unit="joule", description="Spectral Broadening",shape=[2])
    energy_range = Quantity(type = np.float64, unit="joule", description="Energy Range",shape=[2])
    direction = Quantity(type = np.int32, unit="", description="Direction in which the spectra was calculated",shape=[3])
    numberOfFreqs = Quantity(type = np.int32, unit="", description="Number of frequency for which the spectra was calculated")


class RPA_NumSettings(NumericalSettings):
    FFTVecs = Quantity(type = np.int32, unit="", description="FFTGVecs (in Yambo, idk what it actually is)")
    GVecs = Quantity(type = np.float64, unit="joule", description="Number of GVecs in the Hartree Kernel")
    band_range = Quantity(type = np.int32, unit="", description="Band Range",shape=[2])

m_package.__init_metainfo__()

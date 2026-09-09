"""Aperture-time execution finality reference for satellite and NTN systems."""

from .crypto import HMACAuthenticator
from .errors import FinalityError
from .hardware import SimulatedEffectSink
from .models import EpochState, RadioCommand
from .ped import ProtectedEnforcementDomain
from .policy import ConstellationPolicy
from .sink import ApertureFinalitySink
from .store import SQLiteFinalityStore

__all__ = [
    "ApertureFinalitySink", "ConstellationPolicy", "EpochState",
    "FinalityError", "HMACAuthenticator", "ProtectedEnforcementDomain",
    "RadioCommand", "SQLiteFinalityStore", "SimulatedEffectSink",
]


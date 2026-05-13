from .base import BaseDataProvider
from .composite_provider import CompositeProvider

# Active provider — routes stocks to PSX, mutual funds to MUFAP
active_provider: BaseDataProvider = CompositeProvider()
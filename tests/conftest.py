import sys
from unittest.mock import MagicMock

# Mock paramiko to avoid ModuleNotFoundError when importing oprim
sys.modules["paramiko"] = MagicMock()

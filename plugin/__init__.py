"""KiCad legacy ActionPlugin bootstrap. SPDX-License-Identifier: MIT"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent / "lib"))
import pcbnew
from kicad_open_assistant.ui import register
register(pcbnew)

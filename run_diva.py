#!/usr/bin/env python
"""DIVA - Desktop AI Assistant Launcher (feminine counterpart to JARVIS)"""

import os
import sys

os.environ["PYTHONIOENCODING"] = "utf-8"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from diva_app.main import main

if __name__ == "__main__":
    main()

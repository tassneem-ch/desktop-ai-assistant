#!/usr/bin/env python
"""JARVIS - Desktop AI Assistant Launcher"""

import os
import sys

os.environ["PYTHONIOENCODING"] = "utf-8"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jarvis_app.main import main

if __name__ == "__main__":
    main()

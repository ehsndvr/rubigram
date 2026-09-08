#!/usr/bin/env python
"""Django management entry point of the membership worker (run from the repository root)."""

import os
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "membership_worker.project.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

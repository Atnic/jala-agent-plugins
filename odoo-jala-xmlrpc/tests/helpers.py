"""Subprocess fixtures that never consult the host's native credentials/runtime."""

import os
from pathlib import Path


def isolated_environment(directory):
    root = Path(directory)
    modules = root / "python"
    keyring = modules / "keyring"
    keyring.mkdir(parents=True)
    (keyring / "__init__.py").write_text('"""No native backends in test subprocesses."""\n')
    environment = {key: value for key, value in os.environ.items() if not key.startswith("ODOO_")}
    environment["ODOO_JALA_CONFIG_DIR"] = str(root / "state")
    environment["PYTHONPATH"] = os.pathsep.join(filter(None, (str(modules), environment.get("PYTHONPATH"))))
    return environment

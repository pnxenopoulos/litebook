"""Utilities for tests."""

import importlib.util


def check_import(module_name, symbol_name=None):
    """Checks if a module or symbol is importable.

    Args:
        module_name (str): The module to check for availability.
        symbol_name (str, optional): A specific symbol in the module to check. Defaults to None.

    Returns:
        bool: True if importable, False otherwise.
    """
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            print(f"Module {module_name} not found.")
            return False
        if symbol_name:
            module = __import__(module_name, fromlist=[symbol_name])
            if not hasattr(module, symbol_name):
                print(f"Symbol {symbol_name} not found in module {module_name}.")
                return False
        return True
    except ImportError:
        print(f"Failed to import {module_name}.")
        return False

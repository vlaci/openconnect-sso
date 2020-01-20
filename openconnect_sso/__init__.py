try:
    import importlib.metadata as importlib_metadata
except ModuleNotFoundError:
    # Python < 3.8
    import importlib_metadata


_metadata = importlib_metadata.metadata("openconnect-sso")

__version__ = _metadata["Version"]
__description__ = _metadata["Summary"]

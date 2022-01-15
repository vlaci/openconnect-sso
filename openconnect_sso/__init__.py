try:
    import importlib.metadata as importlib_metadata
except ModuleNotFoundError:
    # Python < 3.8
    import importlib_metadata


# _metadata = importlib_metadata.metadata("openconnect-sso")

__version__ = 1
__description__ = "test"

from __future__ import annotations

from importlib.machinery import SourcelessFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

try:
    from api.app.main import create_app as create_combined_app
except ModuleNotFoundError as exc:
    if exc.name != "api":
        raise
    # Compatibility for deployments that still boot `uvicorn main:app`
    # from inside `/api` instead of the repository root.
    from app.main import create_app as create_combined_app


_LEGACY_PYC_CANDIDATES = (
    Path(__file__).with_name("legacy_main.cpython-312.pyc"),
    Path(__file__).with_name("legacy_main.pyc"),
    Path(__file__).with_name("__pycache__") / "legacy_main.cpython-312.pyc",
)


def _load_legacy_module_from_pyc():
    pyc_path = next((path for path in _LEGACY_PYC_CANDIDATES if path.exists()), None)
    if pyc_path is None:
        return None

    loader = SourcelessFileLoader("api._legacy_main_bytecode", str(pyc_path))
    spec = spec_from_loader(loader.name, loader)
    if spec is None:
        raise RuntimeError(f"Failed to build import spec for legacy module: {pyc_path}")

    module = module_from_spec(spec)
    loader.exec_module(module)
    return module


def create_app():
    return create_combined_app()


_legacy_module = _load_legacy_module_from_pyc()
app = create_app()
legacy_app = getattr(_legacy_module, "legacy_app", getattr(_legacy_module, "app", app))

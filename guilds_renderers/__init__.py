"""
GUILDS v2 Renderers Package
============================

Multi-backend rendering system for GUILDS specifications.

Supported backends:
  - html:       Self-contained HTML/CSS/JS SPA
  - python-tk:  Python tkinter desktop application
  - python-qt:  Python PyQt5 desktop application (alias for pyqt5)
  - pyqt5:      Python PyQt5 desktop application
  - pyqt6:      Python PyQt6 desktop application
  - pyside6:    Python PySide6 desktop application
  - cpp-qt:     C++ Qt application (header, source, CMakeLists.txt)
  - cpp-imgui:  C++ Dear ImGui application (header, source)

Usage:
    from guilds_renderers import get_renderer, RENDERERS

    renderer = get_renderer('pyside6')
    code = renderer.render(tree)
"""

from typing import Type, Optional

from .base import (
    BaseRenderer,
    RenderTree,
    RenderNode,
    RenderStyle,
    CERTAINTY_STYLE,
    STAKES_STYLE,
    WEIGHT_STYLE,
    FAILURE_STYLE,
    PHASE_COLOUR,
)

# Lazy imports to avoid circular dependencies and missing optional deps
_renderer_classes: dict[str, str] = {
    'html':       'guilds_renderers.html:HTMLRenderer',
    'python-tk':  'guilds_renderers.python_tk:TkinterRenderer',
    'python-qt':  'guilds_renderers.python_qt:PyQt5Renderer',   # alias for pyqt5
    'pyqt5':      'guilds_renderers.python_qt:PyQt5Renderer',
    'pyqt6':      'guilds_renderers.python_qt:PyQt6Renderer',
    'pyside6':    'guilds_renderers.python_qt:PySide6Renderer',
    'cpp-qt':     'guilds_renderers.cpp_qt:QtCppRenderer',
    'cpp-imgui':  'guilds_renderers.cpp_imgui:ImGuiRenderer',
}

# Cache of loaded renderer classes
_loaded_renderers: dict[str, Type[BaseRenderer]] = {}


def get_renderer(backend: str) -> BaseRenderer:
    """
    Get a renderer instance for the specified backend.

    Args:
        backend: One of 'html', 'python-tk', 'python-qt', 'pyqt5', 'pyqt6',
                 'pyside6', 'cpp-qt', 'cpp-imgui'

    Returns:
        An instance of the appropriate renderer class

    Raises:
        ValueError: If backend is not recognized
        ImportError: If the renderer module cannot be loaded
    """
    if backend not in _renderer_classes:
        available = ', '.join(_renderer_classes.keys())
        raise ValueError(f"Unknown backend '{backend}'. Available: {available}")

    if backend not in _loaded_renderers:
        module_path, class_name = _renderer_classes[backend].split(':')
        try:
            import importlib
            module = importlib.import_module(module_path)
            _loaded_renderers[backend] = getattr(module, class_name)
        except ImportError as e:
            raise ImportError(
                f"Could not load renderer for '{backend}': {e}\n"
                f"Make sure {module_path}.py exists in the guilds_renderers directory."
            )

    return _loaded_renderers[backend]()


def list_backends() -> list[str]:
    """Return list of available backend names."""
    return list(_renderer_classes.keys())


def get_renderer_class(backend: str) -> Type[BaseRenderer]:
    """
    Get the renderer class (not instance) for the specified backend.

    Useful when you need to inspect the class before instantiation.
    """
    # Force load to populate cache
    _ = get_renderer(backend)
    return _loaded_renderers[backend]


# Registry for external renderer registration
RENDERERS: dict[str, Type[BaseRenderer]] = {}


def register_renderer(name: str, renderer_class: Type[BaseRenderer]):
    """
    Register a custom renderer.

    Args:
        name: Backend name to register
        renderer_class: Class that inherits from BaseRenderer
    """
    if not issubclass(renderer_class, BaseRenderer):
        raise TypeError(f"Renderer must inherit from BaseRenderer, got {type(renderer_class)}")
    RENDERERS[name] = renderer_class
    _loaded_renderers[name] = renderer_class
    _renderer_classes[name] = f"{renderer_class.__module__}:{renderer_class.__name__}"


__all__ = [
    # Base classes
    'BaseRenderer',
    'RenderTree',
    'RenderNode',
    'RenderStyle',

    # Style constants
    'CERTAINTY_STYLE',
    'STAKES_STYLE',
    'WEIGHT_STYLE',
    'FAILURE_STYLE',
    'PHASE_COLOUR',

    # Registry functions
    'get_renderer',
    'list_backends',
    'get_renderer_class',
    'register_renderer',
    'RENDERERS',
]

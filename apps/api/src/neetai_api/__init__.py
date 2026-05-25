"""FastAPI transport layer.

This package is deliberately thin:
    * routers translate HTTP to typed domain calls
    * a small DI container assembles adapters into ports
    * startup/shutdown hooks own resource lifecycles

No business logic lives here. If you want to add a rule, classification, or
decision — it belongs in one of the domain packages.
"""

__version__ = "0.1.0"

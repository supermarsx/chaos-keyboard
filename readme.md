# chaos-keyboard

Chaotic virtual keyboard that helps you test your machine's security while
staying safely inside simulation-only guardrails.

## Effect plugin architecture

Chaos Keyboard now supports drop-in effect plugins discovered from
``chaos_keyboard/effects`` subdirectories. Each plugin places its implementation
in an ``effect.py`` module that exposes a ``register(app)`` function. During
startup the loader imports every such module inside a sandboxed environment and
invokes ``register`` with a ``PluginApp`` helper.

```text
chaos_keyboard/
└── effects/
    ├── existing_effects.py
    └── my_plugin/
        └── effect.py  # contains register(app)
```

The ``PluginApp`` exposes two helpers to register new effects with the global
registry:

* ``app.register_effect(name, *, capabilities=None)`` — decorator mirroring the
  built-in ``chaos_keyboard.effects.register_effect`` helper.
* ``app.register_factory(name, factory, *, capabilities=None)`` — register a
  factory function directly.

Factories receive the active ``SafetyContext`` and ``EventBus`` instances.
Effects must implement ``start``, ``stop`` and ``status`` methods and declare a
``capabilities`` frozenset describing their requirements (see
``tests/sample_plugins`` for reference implementations).

### Sandbox behaviour

Plugins run inside a lightweight sandbox that disallows importing ``subprocess``,
``socket`` and ``ctypes`` so that simulation builds remain side-effect free. The
``PluginApp`` exposes ``app.developer_mode_enabled`` so authors can detect when a
developer override is active. To opt into unsafe imports (for local development
only) set the ``CHAOS_KEYBOARD_ALLOW_UNSAFE_PLUGINS=1`` environment variable
before launching the application or running the loader.

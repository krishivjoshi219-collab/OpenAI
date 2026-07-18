# Architecture notes

The MVP uses a layered, ports-and-adapters-friendly structure:

- `ui` renders Streamlit views and owns no business decisions.
- `routers` maps UI or future API inputs to application services.
- `services` will contain use cases and depend on interfaces, not vendor SDKs.
- `business` will hold domain concepts plus adapters for systems such as Odoo.
- `ai`, `database`, `memory`, and `notifications` are infrastructure boundaries.

Keep vendor-specific calls confined to their boundary modules. For example, an Odoo client should implement a business-facing repository or gateway interface, while OpenAI calls remain in `app/ai`.


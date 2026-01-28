from src.interfaces.types import Plugin, Tool

async def hello_world(args: dict) -> str:
    return f"Hello, {args.get('name', 'world')}!"

class ExamplePlugin(Plugin):
    def on_load(self) -> None:
        print("Example Plugin loaded!")

plugin = ExamplePlugin(
    name="ExamplePlugin",
    description="An example plugin to test the system.",
    tools=[
        Tool(
            name="hello_world",
            description="Says hello.",
            input_schema={"name": "string"},
            handler=hello_world
        )
    ]
)

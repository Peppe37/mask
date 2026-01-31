from src.interfaces.types import Plugin, Tool
import random

async def get_weather(args: dict) -> str:
    location = args.get("location", "Unknown Location")
    # Simulate weather data
    temps = [20, 22, 18, 25, 30, 15]
    conditions = ["Sunny", "Cloudy", "Rainy", "Partly Cloudy"]
    
    temp = random.choice(temps)
    condition = random.choice(conditions)
    
    return f"The current weather in {location} is {temp}°C and {condition}."

class WeatherPlugin(Plugin):
    def on_load(self) -> None:
        print("Weather Plugin loaded!")

plugin = WeatherPlugin(
    name="WeatherPlugin",
    description="A plugin to fetch weather information.",
    tools=[
        Tool(
            name="get_weather",
            description="Fetches the current weather for a specific location.",
            input_schema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA"
                    }
                },
                "required": ["location"]
            },
            handler=get_weather
        )
    ]
)

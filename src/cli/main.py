import typer
import asyncio
from rich.console import Console
from rich.prompt import Prompt
from src.core.database.postgres import check_postgres_connection
from src.core.database.neo4j import neo4j_db
from src.core.database.qdrant import check_qdrant_connection
from src.core.agents.coordinator import coordinator
from src.core.tool_registry import tool_registry

app = typer.Typer()
console = Console()

@app.command()
def check_health():
    """Checks connections to databases and services."""
    async def _check():
        console.print("[bold blue]Checking Postgres...[/bold blue]")
        pg = await check_postgres_connection()
        if pg:
            console.print("[green]Postgres connected.[/green]")
        else:
            console.print("[red]Postgres failed.[/red]")

        console.print("[bold blue]Checking Neo4j...[/bold blue]")
        neo = await neo4j_db.check_connection()
        if neo:
            console.print("[green]Neo4j connected.[/green]")
        else:
            console.print("[red]Neo4j failed.[/red]")

        console.print("[bold blue]Checking Qdrant...[/bold blue]")
        qd = await check_qdrant_connection()
        if qd:
            console.print("[green]Qdrant connected.[/green]")
        else:
            console.print("[red]Qdrant failed.[/red]")

    asyncio.run(_check())

@app.command()
def chat():
    """Starts an interactive chat session with the Coordinator Agent."""
    tool_registry.initialize()
    console.print("[bold yellow]Starting Multi-Agent Framework...[/bold yellow]")
    console.print(f"Loaded tools: {[t['name'] for t in tool_registry.list_tools()]}")
    console.print("[bold green]Chat started. Type 'exit' to quit.[/bold green]")

    async def _chat_loop():
        history = []
        while True:
            user_input = Prompt.ask("[bold cyan]You[/bold cyan]")
            if user_input.lower() in ["exit", "quit"]:
                break

            with console.status("[bold green]Agent thinking...[/bold green]"):
                response = await coordinator.run(user_input, history)

            console.print(f"[bold magenta]Coordinator:[/bold magenta] {response}")
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": str(response)})

    asyncio.run(_chat_loop())

if __name__ == "__main__":
    app()

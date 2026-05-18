import typer
from rich.console import Console
from rich.rule import Rule
from rich.table import Table
from rich import box

from src import enums


app = typer.Typer()
console = Console()

@app.command()
def calculate_route(
    source: tuple[float, float],
    target: tuple[float, float],
    mode: list[enums.RouteMode] = typer.Option(
        None, 
        "--mode", "-m"
    )
):
    if not mode:
        print("You have to pass at least one mode to calculate route.")
        return

    for m in mode:
        # Tu będzie wywołanie algorytmu
        nodes = [
            (53.1325, 23.1688),
            (52.8800, 22.1500),
            (52.2297, 21.0122),
            (50.8118, 20.6275),
            (50.0647, 19.9450)
        ]
        cost = 152        
        
        table = Table(
            title=f"🗺️  Shortest route summary ({m})", 
            box=box.SIMPLE,
            title_justify="left",
            title_style="bold cyan"
        )
        table.add_column("Number", justify="right", style="dim")
        table.add_column("Latitude", justify="right")
        table.add_column("Longitude", justify="right")
        table.add_column("Status", justify="right")

        for index, (lat, lon) in enumerate(nodes, start=1):
            if index == 1:
                node_type = f"[bold green]🟢 {enums.NodeType.START}[/bold green]"
            elif index == len(nodes):
                node_type = f"[bold red]📍 {enums.NodeType.END}[/bold red]"
            else:
                node_type = f"[bold] {enums.NodeType.INTERMEDIATE}[/bold]"

            table.add_row(
                str(index),
                f"{lat:.4f}",
                f"{lon:.4f}",
                node_type
            )

        console.print(Rule(style="cyan"))
        console.print(table)
        console.print(f"\n[dim]Cost:[/dim] [bold]{cost}[/bold]")


if __name__ == "__main__":
    app()

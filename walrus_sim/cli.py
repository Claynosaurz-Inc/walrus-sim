import typer
from pathlib import Path
from datetime import datetime
import shutil
from walrus_sim.processor import process_images, upload_images
from walrus_sim.report import generate_summary_files

app = typer.Typer(help="Walrus Storage Simulation CLI")
utils_app = typer.Typer(help="Utility commands")
app.add_typer(utils_app, name="utils")

def ensure_walrus_installed():
    if shutil.which("walrus") is None:
        typer.echo("❌ Walrus CLI not found. Please install it from https://github.com/MystenLabs/walrus.", err=True)
        raise typer.Exit(code=1)

def ensure_sui_installed():
    if shutil.which("sui") is None:
        typer.echo("❌ SUI CLI not found. Please install it from https://docs.sui.io/build/install", err=True)
        raise typer.Exit(code=1)

@app.command()
def simulate(
    path: Path = typer.Option("./images", help="Directory with .webp files"),
    context: str = typer.Option("mainnet", help="Storage context (mainnet or testnet)"),
    epochs: str = typer.Option("max", help="Epochs to simulate (default: max)"),
    share: bool = typer.Option(False, help="Enable --share flag"),
    resume: bool = typer.Option(False, help="Retry failed images only"),
    fresh: bool = typer.Option(False, help="Reprocess all images"),
    workers: int = typer.Option(None, help="Number of parallel workers (default: CPU count)"),
    verify: bool = typer.Option(False, help="Check all blobIds for uniqueness."),
    clean: bool = typer.Option(True, help="Delete per-image .json files after run."),
    log: bool = typer.Option(False, help="Generate a run log with metadata and stats.")
):
    """Run the storage simulation."""
    ensure_walrus_installed()
    ensure_sui_installed()

    start_time = datetime.utcnow()
    interrupted = False

    try:
        results, errors, totals = process_images(
            path=path,
            context=context,
            epochs=epochs,
            share=share,
            resume=resume,
            fresh=fresh,
            workers=workers,
            verify=verify,
            clean=clean
        )
    except KeyboardInterrupt:
        interrupted = True
        typer.echo("\n🛑 Interrupted by user. Saving partial results...")
        results, errors, totals = process_images(
            path=path,
            context=context,
            epochs=epochs,
            share=share,
            resume=False,
            fresh=False,
            workers=workers,
            verify=verify,
            clean=False
        )

    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()

    metadata = {
        "timestamp": start_time.isoformat() + "Z",
        "duration_seconds": duration,
        "context": context,
        "epochs": epochs,
        "path": str(path),
        "share": share,
        "verify": verify,
        "clean": clean,
        "workers": workers or "auto",
        "interrupted": interrupted,
    }

    generate_summary_files(path, results, errors, totals, metadata=metadata if log else None)

@app.command()
def upload(
    path: Path = typer.Option("./images", help="Directory with .webp files"),
    context: str = typer.Option("mainnet", help="Storage context (mainnet or testnet)"),
    epochs: str = typer.Option("max", help="Epochs to store (default: max)"),
    share: bool = typer.Option(False, help="Enable --share flag"),
    workers: int = typer.Option(None, help="Number of parallel workers (default: CPU count)")
):
    """Upload blobs to Walrus (after validating wallet balance)."""
    ensure_walrus_installed()
    ensure_sui_installed()

    typer.echo("🚀 Starting upload of images to Walrus storage...")
    results, errors, totals = upload_images(
        path=path,
        context=context,
        epochs=epochs,
        share=share,
        workers=workers
    )

    generate_summary_files(path, results, errors, totals, metadata=None)

@utils_app.command()
def docs():
    """Print full CLI documentation."""
    from typer.main import get_command
    import click
    cmd = get_command(app)
    with click.Context(cmd) as ctx:
        click.echo(cmd.get_help(ctx))

@utils_app.command()
def check():
    """Check if Walrus and SUI CLI are installed."""
    ensure_walrus_installed()
    typer.echo("✅ Walrus CLI is installed and ready.")
    ensure_sui_installed()
    typer.echo("✅ SUI CLI is installed and ready.")

if __name__ == "__main__":
    app()
# 🧊 walrus-sim

Simulate and estimate storage costs on the [Walrus Protocol](https://www.walrus.xyz) using real image files and the official Walrus CLI.

Supports:
- 📦 Cost simulation with dry-run mode
- ☁️ Actual upload to Walrus storage
- ✅ Balance checks using `sui client balance`
- 📊 HTML reports with blob size, cost, blobId, duplication, and expiration metadata
- 🛠 Full CLI powered by [Typer](https://typer.tiangolo.com/)
- ⚡️ Multi-process for fast execution

---

## 🧰 Installation

### ✅ Option 1: Using Poetry (for development)

```bash
git clone https://github.com/your-org/walrus-sim.git
cd walrus-sim
poetry install
poetry run walrus-sim --help
```

### ✅ Option 2: Download prebuilt CLI

Visit the [Releases page](https://github.com/your-org/walrus-sim/releases) and download the latest:

```bash
chmod +x walrus-sim.pyz
./walrus-sim.pyz simulate --help
```

---

## 🚀 CLI Commands

### `simulate`

Run a dry-run simulation of uploading files and generate a full cost + metadata report.

```bash
walrus-sim simulate --path ./generated --context mainnet --epochs max --workers 4 --verify
```

**Options**:
- `--path`: Folder containing `.webp`, `.jpg`, `.png`, `.gif` (default: `./generated`)
- `--context`: `mainnet` or `testnet` (default: `mainnet`)
- `--epochs`: How long to store blobs (`max` or number)
- `--workers`: Number of concurrent workers (default: CPU count)
- `--resume`: Retry failed or missing files only
- `--fresh`: Reprocess all, deleting old `.json` files
- `--share`: Include `--share` flag in the Walrus command
- `--verify`: Check for duplicate blobIds
- `--clean`: Delete intermediate `.json` per-image
- `--log`: Save a run metadata log and open HTML summary

---

### `upload`

Actually uploads the files to Walrus storage, with pre-checks:

```bash
walrus-sim upload --path ./generated --context mainnet --share --epochs 3
```

✅ Includes:
- `sui client balance --json` validation
- WAL and SUI balance check before proceeding
- Dry-run cost check before actual storage
- Uploads only if wallet has sufficient FROST and SUI

---

### `docs`

Prints the full CLI usage documentation directly to the console:

```bash
walrus-sim docs
```

---

## 📊 HTML Report

The CLI auto-generates a beautiful Tailwind-powered summary:

- ✅ Image name
- ✅ Blob ID
- ✅ Size in GB
- ✅ Storage cost in WAL
- ✅ Whether it's shared
- ✅ Duplication info
- ✅ Blob expiration epoch

---

## 🔒 Prerequisites

Make sure you have both installed and available in your terminal:

- `walrus` CLI
- `sui` CLI

You can verify with:

```bash
which walrus
which sui
```

---

## 🛠 Dev Commands

```bash
# Run CLI with local source
poetry run walrus-sim simulate ...

# Build standalone executable
poetry run shiv -c walrus-sim -o dist/walrus-sim.pyz -p '/usr/bin/env python3' .

# Run standalone
./dist/walrus-sim.pyz simulate --help
```

---

## 📦 Releases

GitHub Actions will automatically build and upload `walrus-sim.pyz` on every new Git tag.

```bash
git tag v0.1.0
git push origin v0.1.0
```

---

## 👋 License

MIT – feel free to fork, adapt, or integrate with your own SUI or Walrus workflow!

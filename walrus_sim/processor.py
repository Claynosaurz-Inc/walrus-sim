import os
import json
import subprocess
from pathlib import Path
from tqdm import tqdm
from multiprocessing import cpu_count
from concurrent.futures import ProcessPoolExecutor
from typing import List, Dict, Tuple

FROST_PER_WAL = 1_000_000_000

# ------------------------ WALRUS SIMULATE ------------------------

def run_walrus_command(image_path: Path, context: str, epochs: str, share: bool, dry_run: bool = True) -> Dict:
    cmd = ["walrus", "store", str(image_path), "--context", context, "--epochs", epochs, "--json"]
    if dry_run:
        cmd.append("--dry-run")
    if share:
        cmd.append("--share")
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout)[0]

def get_sui_balances() -> Dict:
    result = subprocess.run(["sui", "client", "balance", "--json"], capture_output=True, text=True)
    return json.loads(result.stdout)

def save_json(output_path: Path, data: dict):
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

def get_balances(balances):
    # Initialize results
    sui_balance = 0
    wal_balance = 0
    
    # Iterate through the outer list
    for token_group in balances[0]:  # balances[0] because the data is nested in first element
        metadata, coins = token_group  # Each group has metadata and coins list
        
        # Check symbol and get balance
        if metadata.get("symbol") == "SUI":
            sui_balance = int(coins[0]["balance"])  # Convert string to int
        elif metadata.get("symbol") == "WAL":
            wal_balance = int(coins[0]["balance"])  # Convert string to int
            
    # Convert from smallest unit (considering 9 decimals)
    sui_balance = sui_balance / 10**9
    wal_balance = wal_balance / 10**9
    
    return sui_balance, wal_balance

def upload_images(path: Path, context: str, epochs: str, share: bool, workers: int = None) -> Tuple[List[Dict], List[Dict], Dict]:
    image_paths = [p for p in path.rglob("*") if p.suffix.lower() in {".webp", ".png", ".jpg", ".jpeg", ".gif"}]
    results, errors = [], []
    workers = workers or cpu_count()

    balances = get_sui_balances()
    sui_balance, wal_balance = get_balances(balances)

    # Check balances - modified to handle float values correctly
    if not sui_balance or sui_balance <= 0:  # Check if zero or negative
        raise RuntimeError("❌ SUI balance is missing or zero.")
    if not wal_balance:  # Only checking if None, allowing zero balance
        raise RuntimeError("❌ WAL/FROST balance not found.")

    wal_available = wal_balance  # Use the float value directly

    for img_path in tqdm(image_paths, desc="Uploading"):
        try:
            # Estimate cost
            dry_info = run_walrus_command(img_path, context, epochs, share, dry_run=True)
            cost = int(dry_info["storageCost"]) / 10**9  # Convert cost to same unit as wal_balance
            if cost > wal_available:
                raise RuntimeError(f"❌ Not enough WAL balance to store {img_path.name}")

            # Execute actual store
            real_info = run_walrus_command(img_path, context, epochs, share, dry_run=False)
            output_path = img_path.with_suffix(".stored.json")
            save_json(output_path, real_info)
            blob_info = real_info["blobStoreResult"]["newlyCreated"]["blobObject"]
            results.append({
                "name": img_path.name,
                "blobId": blob_info["blobId"],
                "size": blob_info["size"],
                "cost": real_info["blobStoreResult"]["newlyCreated"]["cost"],
                "sharedBlobObject": real_info["blobStoreResult"]["newlyCreated"].get("sharedBlobObject", "")
            })

            wal_available -= cost  # Deduct from remaining balance

        except Exception as e:
            errors.append({"image": str(img_path), "error": str(e)})

    total_cost = sum(r["cost"] for r in results) / 10**9  # Convert to human-readable units
    total_size = sum(r["size"] for r in results)
    totals = {
        "unencoded": total_size,
        "encoded": total_size,  # Assume encoded size same for now
        "cost": total_cost,
        "totalBlobIds": len(results),
        "uniqueBlobIds": len(set(r["blobId"] for r in results)),
        "duplicateBlobIds": len(results) - len(set(r["blobId"] for r in results)),
        "hasDuplicates": len(results) != len(set(r["blobId"] for r in results))
    }
    totals["wallet"] = {
        "sui_balance": sui_balance,  # Already in human-readable units
        "wal_balance": wal_balance   # Already in human-readable units
    }
    return results, errors, totals

# ------------------------ WALRUS SIMULATE END ------------------------

def process_images(path: Path, context: str, epochs: str, share: bool, resume: bool, fresh: bool, workers: int, verify: bool, clean: bool) -> Tuple[List[Dict], List[Dict], Dict]:
    image_paths = [p for p in path.rglob("*") if p.suffix.lower() in {".webp", ".png", ".jpg", ".jpeg", ".gif"}]
    json_paths = {p.with_suffix(".json") for p in image_paths}

    if fresh:
        for p in json_paths:
            if p.exists():
                p.unlink()

    tasks = []
    for img_path in image_paths:
        json_path = img_path.with_suffix(".json")
        if resume and not json_path.exists():
            continue
        if not resume and json_path.exists():
            continue
        tasks.append(img_path)

    results, errors = [], []
    args = [(p, context, epochs, share) for p in tasks]
    with ProcessPoolExecutor(max_workers=workers or cpu_count()) as executor:
        for result in tqdm(executor.map(simulate_image_wrapper, args), total=len(tasks)):
            if isinstance(result, dict) and "error" in result:
                errors.append(result)
            else:
                results.append(result)

    # BlobId verification
    if verify:
        blob_ids = [r["blobId"] for r in results]
        unique_ids = set(blob_ids)
        duplicates = len(blob_ids) - len(unique_ids)
    else:
        duplicates = 0

    # Clean .json files
    if clean:
        for p in json_paths:
            if p.exists():
                p.unlink()

    total_cost = sum(r["storageCost"] for r in results)
    total_unencoded = sum(r["unencodedSize"] for r in results)
    total_encoded = sum(r.get("encodedSize", 0) for r in results)

    totals = {
        "unencoded": total_unencoded,
        "encoded": total_encoded,
        "cost": total_cost,
        "totalBlobIds": len(results),
        "uniqueBlobIds": len(set(r["blobId"] for r in results)),
        "duplicateBlobIds": duplicates,
        "hasDuplicates": duplicates > 0,
    }

    return results, errors, totals

def simulate_image(path: Path, context: str, epochs: str, share: bool) -> Dict:
    try:
        output = run_walrus_command(path, context, epochs, share, dry_run=True)
        blob = output[0] if isinstance(output, list) else output
        result = {
            "img_path": str(path),
            "blobId": blob["blobId"],
            "unencodedSize": blob["unencodedSize"],
            "encodedSize": blob["encodedSize"],
            "storageCost": blob["storageCost"],
            "encodingType": blob.get("encodingType", "")
        }
        with open(path.with_suffix(".json"), "w") as f:
            json.dump(result, f, indent=2)
        return result
    except Exception as e:
        return {"image": str(path), "error": str(e)}

def simulate_image_wrapper(args):
    return simulate_image(*args)

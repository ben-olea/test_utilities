import os, sys, json, tarfile, hashlib
import requests


# supabase client info
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt4cWh6bmhtcml1cml2bXZoYWV2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTY5MTExMzg2MSwiZXhwIjoyMDA2Njg5ODYxfQ.uUe-SRlGnUOjnzHP58Dth_xvaC4ODsKF9hl02kAAWE8"
API_HOST = "https://api.oleaedge.com"

# use ~/Documents/camera_test/ as working directory
ARTIFACT_DIR = os.path.join(os.path.expanduser("~"), "Documents", "camera_test", "artifacts")

def ensure_artifact_dir():
    if not os.path.exists(ARTIFACT_DIR):
        os.makedirs(ARTIFACT_DIR)
        print(f"Created directory: {ARTIFACT_DIR}")
    return ARTIFACT_DIR

def get_local_bundle_id():
    bundle_id_path = os.path.join(ARTIFACT_DIR, "bundle_id.txt")
    if os.path.exists(bundle_id_path):
        with open(bundle_id_path, "r") as f:
            return f.read().strip()
    return "None"

def get_latest_bundle(bundle_id="none"): 
    url = f"{API_HOST}/functions/v1/provision"

    payload = json.dumps({
    "olea_id": "20000000"
    })
    headers = {
    'apikey': API_KEY,
    'If-None-Match': bundle_id,
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {API_KEY}'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    print(f"Status code: {response.status_code} - {response.reason}")

    if response.status_code == 200:
        ensure_artifact_dir()

        # Save binary bundle
        bundle_path = os.path.join(ARTIFACT_DIR, "bundle.tar.gz")
        with open(bundle_path, "wb") as f:
            f.write(response.content)
        print(f"Bundle saved to: {bundle_path}")

        # Extract bundle
        with tarfile.open(bundle_path, "r:gz") as tar:
            tar.extractall(path=ARTIFACT_DIR)
        print(f"Bundle extracted to: {ARTIFACT_DIR}")

        # Update stored bundle ID from ETag header
        new_bundle_id = response.headers.get("ETag").replace("W/", "")
        if new_bundle_id:
            bundle_id_path = os.path.join(ARTIFACT_DIR, "bundle_id.txt")
            with open(bundle_id_path, "w") as f:
                f.write(new_bundle_id.strip('"'))
            print(f"Bundle ID updated: {new_bundle_id}")

        return bundle_path
    else:
        print(f"No update or error: {response.text}")
        return None



FIRMWARE_DIR = os.path.join(ARTIFACT_DIR, "tasks", "0", "firmware")
HEAD_FIRMWARE = "led_control.uf2"

def get_head_fw_version():
    """Return expected head firmware version string from inventory."""
    inventory_path = os.path.join(FIRMWARE_DIR, "firmware_inventory.json")
    with open(inventory_path, "r") as f:
        return json.load(f)["head"]["fw_version"]

def verify_firmware():
    """Verify led_control.uf2 exists and matches hash in firmware_inventory.json.
    Returns (fw_version, uf2_path) on success, raises on failure."""
    inventory_path = os.path.join(FIRMWARE_DIR, "firmware_inventory.json")
    if not os.path.exists(inventory_path):
        raise FileNotFoundError(f"firmware_inventory.json not found: {inventory_path}")

    with open(inventory_path, "r") as f:
        inventory = json.load(f)

    head = inventory.get("head")
    if not head:
        raise KeyError("'head' entry missing from firmware_inventory.json")

    fw_version = head["fw_version"]
    expected_hash = head["hash"]

    uf2_path = os.path.join(FIRMWARE_DIR, HEAD_FIRMWARE)
    if not os.path.exists(uf2_path):
        raise FileNotFoundError(f"{HEAD_FIRMWARE} not found: {uf2_path}")

    with open(uf2_path, "rb") as f:
        actual_hash = hashlib.md5(f.read()).hexdigest()

    if actual_hash != expected_hash:
        raise ValueError(f"Hash mismatch for {HEAD_FIRMWARE}: expected {expected_hash}, got {actual_hash}")

    print(f"Firmware verified: {HEAD_FIRMWARE} v{fw_version} @ {uf2_path}")
    return fw_version, uf2_path


if __name__ == "__main__":
    try:
        ensure_artifact_dir()
        local_bundle_id = get_local_bundle_id()
        print(f"Local bundle ID: {local_bundle_id}")
        get_latest_bundle(local_bundle_id)
        exit(0)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
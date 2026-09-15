#!/usr/bin/env python3

import os
import shutil
import subprocess
import sys
from pathlib import Path


SSH_DIR = Path.home() / ".ssh"
KEY_FILE = SSH_DIR / "id_ed25519"
PUBLIC_KEY_FILE = SSH_DIR / "id_ed25519.pub"


def run(cmd, check=False):
    print(f"\n$ {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        text=True,
        capture_output=True
    )

    if result.stdout:
        print(result.stdout.strip())

    if result.stderr:
        print(result.stderr.strip())

    if check and result.returncode != 0:
        sys.exit(result.returncode)

    return result


def main():
    print("=" * 60)
    print(" GitHub SSH Key Setup")
    print("=" * 60)

    # ---------------------------------------------------------
    # 1. Check required commands
    # ---------------------------------------------------------
    print("\n[1] Checking required commands...")

    for command in ["ssh", "ssh-keygen"]:
        path = shutil.which(command)

        if path:
            print(f"OK: {command} -> {path}")
        else:
            print(f"ERROR: {command} not found.")
            print("Install it with:")
            print("  sudo apt update")
            print("  sudo apt install openssh-client")
            sys.exit(1)

    # ---------------------------------------------------------
    # 2. Create ~/.ssh
    # ---------------------------------------------------------
    print("\n[2] Checking ~/.ssh directory...")

    SSH_DIR.mkdir(mode=0o700, exist_ok=True)
    os.chmod(SSH_DIR, 0o700)

    print(f"OK: {SSH_DIR}")

    # ---------------------------------------------------------
    # 3. Check existing Ed25519 key
    # ---------------------------------------------------------
    print("\n[3] Checking SSH key...")

    if KEY_FILE.exists() and PUBLIC_KEY_FILE.exists():
        print("Existing Ed25519 SSH key found:")
        print(f"  Private: {KEY_FILE}")
        print(f"  Public : {PUBLIC_KEY_FILE}")

    else:
        print("No Ed25519 key found.")
        print("Generating a new key...")

        result = subprocess.run(
            [
                "ssh-keygen",
                "-t",
                "ed25519",
                "-f",
                str(KEY_FILE),
                "-N",
                "",
                "-C",
                f"github-{os.getenv('USER', 'ubuntu')}",
            ],
            text=True
        )

        if result.returncode != 0:
            print("ERROR: Failed to generate SSH key.")
            sys.exit(1)

        print("SSH key generated successfully.")

    # ---------------------------------------------------------
    # 4. Fix permissions
    # ---------------------------------------------------------
    print("\n[4] Setting permissions...")

    os.chmod(SSH_DIR, 0o700)

    if KEY_FILE.exists():
        os.chmod(KEY_FILE, 0o600)

    if PUBLIC_KEY_FILE.exists():
        os.chmod(PUBLIC_KEY_FILE, 0o644)

    print("OK")

    # ---------------------------------------------------------
    # 5. Start ssh-agent and add key
    # ---------------------------------------------------------
    print("\n[5] Checking ssh-agent...")

    agent_check = subprocess.run(
        ["ssh-add", "-l"],
        text=True,
        capture_output=True
    )

    if agent_check.returncode != 0:
        print("ssh-agent does not appear to be running.")
        print("Trying to start ssh-agent...")

        agent = subprocess.run(
            ["ssh-agent", "-s"],
            text=True,
            capture_output=True
        )

        if agent.returncode == 0:
            print(agent.stdout.strip())
            print()
            print("NOTE: Run these commands manually if ssh-agent")
            print("environment variables were not exported:")
            print()
            print("  eval \"$(ssh-agent -s)\"")
            print(f"  ssh-add {KEY_FILE}")
        else:
            print("Could not start ssh-agent automatically.")

    else:
        print("ssh-agent is running.")

        # Check whether this key is already loaded
        keys = subprocess.run(
            ["ssh-add", "-l"],
            text=True,
            capture_output=True
        )

        if str(KEY_FILE) not in keys.stdout:
            print("Adding key to ssh-agent...")
            subprocess.run(
                ["ssh-add", str(KEY_FILE)],
                text=True
            )

    # ---------------------------------------------------------
    # 6. Show fingerprint
    # ---------------------------------------------------------
    print("\n[6] SSH key fingerprint...")

    run([
        "ssh-keygen",
        "-lf",
        str(PUBLIC_KEY_FILE)
    ])

    # ---------------------------------------------------------
    # 7. Test GitHub SSH
    # ---------------------------------------------------------
    print("\n[7] Testing GitHub SSH connection...")

    result = subprocess.run(
        [
            "ssh",
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=accept-new",
            "-T",
            "git@github.com"
        ],
        text=True,
        capture_output=True
    )

    output = (result.stdout + result.stderr).strip()

    if "successfully authenticated" in output:
        print("\nSUCCESS!")
        print(output)

    elif "Hi " in output and "GitHub" in output:
        print("\nSUCCESS!")
        print(output)

    else:
        print("\nGitHub authentication is not yet successful.")
        print(output)

    # ---------------------------------------------------------
    # 8. Print public key
    # ---------------------------------------------------------
    print("\n")
    print("=" * 60)
    print(" COPY THIS PUBLIC KEY TO GITHUB")
    print("=" * 60)
    print()

    public_key = PUBLIC_KEY_FILE.read_text().strip()

    print(public_key)

    print()
    print("=" * 60)
    print("GitHub:")
    print("Settings -> SSH and GPG keys -> New SSH key")
    print("=" * 60)

    # ---------------------------------------------------------
    # 9. Show useful commands
    # ---------------------------------------------------------
    print("\nAfter adding the key to GitHub, test with:")
    print()
    print("  ssh -T git@github.com")
    print()
    print("Then test your repository:")
    print()
    print("  git remote -v")
    print("  git push origin master")
    print()


if __name__ == "__main__":
    main()

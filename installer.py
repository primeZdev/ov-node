import os
import pexpect, sys
import subprocess
import shutil
import requests
from uuid import uuid4
from colorama import Fore, Style


def install_ovnode():
    try:
        # Get the current script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_ovpn_script = os.path.join(script_dir, "openvpn-install.sh")
        target_ovpn_script = "/root/openvpn-install.sh"
        
        # Copy openvpn-install.sh from current directory to /root/
        if os.path.exists(project_ovpn_script):
            print("Using openvpn-install.sh from project directory...")
            shutil.copy(project_ovpn_script, target_ovpn_script)
            # Make sure the script is executable
            os.chmod(target_ovpn_script, 0o755)
        else:
            print("openvpn-install.sh not found in project, downloading...")
            subprocess.run(
                ["wget", "https://git.io/vpn", "-O", target_ovpn_script], check=True
            )

        # Run the OpenVPN installer script (now with automated defaults)
        print("Running OpenVPN installer...")
        subprocess.run(
            ["/usr/bin/bash", target_ovpn_script],
            check=True
        )

        # Copy .env.example to .env in the current directory
        env_example = os.path.join(script_dir, ".env.example")
        env_file = os.path.join(script_dir, ".env")
        
        if os.path.exists(env_example):
            shutil.copy(env_example, env_file)
        else:
            print("Warning: .env.example not found")

        # OV-Node configuration prompts
        example_uuid = str(uuid4())
        SERVICE_PORT = input("OV-Node service port (default 9090): ") or "9090"
        API_KEY = input(f"OV-Node API key (example: {example_uuid}): ") or example_uuid

        replacements = {
            "SERVICE_PORT": SERVICE_PORT,
            "API_KEY": API_KEY,
        }

        lines = []
        with open(env_file, "r") as f:
            for line in f:
                for key, value in replacements.items():
                    if line.startswith(f"{key}="):
                        line = f"{key}={value}\n"
                lines.append(line)

        with open(env_file, "w") as f:
            f.writelines(lines)

        run_ovnode()
        input("Press Enter to return to the menu...")
        menu()

    except Exception as e:
        print("Error occurred during installation:", e)
        input("Press Enter to return to the menu...")
        menu()


def update_ovnode():
    try:
        install_dir = "/opt/ov-node"
        venv_dir = os.path.join(install_dir, "venv")
        env_file = os.path.join(install_dir, ".env")
        backup_env = "/tmp/ovnode_env_backup"

        # Backup .env file
        if os.path.exists(env_file):
            shutil.copy2(env_file, backup_env)

        # Check if directory exists and is a git repository
        if os.path.exists(install_dir):
            os.chdir(install_dir)
            if os.path.exists(os.path.join(install_dir, ".git")):
                print(Fore.YELLOW + "Pulling latest changes from repository..." + Style.RESET_ALL)
                subprocess.run(["git", "fetch", "--all"], check=True)
                subprocess.run(["git", "reset", "--hard", "origin/main"], check=True)
                subprocess.run(["git", "pull", "origin", "main"], check=True)
            else:
                # If not a git repo, clone it
                print(Fore.YELLOW + "Cloning repository..." + Style.RESET_ALL)
                shutil.rmtree(install_dir)
                subprocess.run(
                    ["git", "clone", "https://github.com/primeZdev/ov-node.git", install_dir],
                    check=True
                )
                os.chdir(install_dir)
        else:
            # Directory doesn't exist, clone it
            print(Fore.YELLOW + "Cloning repository..." + Style.RESET_ALL)
            subprocess.run(
                ["git", "clone", "https://github.com/primeZdev/ov-node.git", install_dir],
                check=True
            )
            os.chdir(install_dir)

        # Restore .env file
        if os.path.exists(backup_env):
            shutil.move(backup_env, env_file)

        print(Fore.YELLOW + "Creating virtual environment..." + Style.RESET_ALL)
        if not os.path.exists(venv_dir):
            subprocess.run(["/usr/bin/python3", "-m", "venv", venv_dir], check=True)

        print(Fore.YELLOW + "Installing requirements..." + Style.RESET_ALL)
        pip_path = os.path.join(venv_dir, "bin", "pip")
        subprocess.run([pip_path, "install", "--upgrade", "pip"], check=True)
        
        requirements_file = os.path.join(install_dir, "requirements.txt")
        if os.path.exists(requirements_file):
            subprocess.run([pip_path, "install", "-r", requirements_file], check=True)
        else:
            print(Fore.YELLOW + "requirements.txt not found, installing basic dependencies..." + Style.RESET_ALL)
            subprocess.run([pip_path, "install", "fastapi", "uvicorn", "psutil", "pydantic_settings", 
                          "python-dotenv", "colorama", "pexpect", "requests"], check=True)

        subprocess.run(["systemctl", "restart", "ov-node"], check=True)

        print(Fore.GREEN + "OV-Node updated successfully!" + Style.RESET_ALL)
        input("Press Enter to return to the menu...")
        menu()

    except Exception as e:
        print(Fore.RED + f"Update failed: {e}" + Style.RESET_ALL)
        input("Press Enter to return to the menu...")
        menu()


def uninstall_ovnode():
    try:
        uninstall = input("Do you want to uninstall OV-Node? (y/n): ")
        if uninstall.lower() != "y":
            print("Uninstallation canceled.")
            menu()

        bash = pexpect.spawn("bash /root/openvpn-install.sh", timeout=300)
        subprocess.run("clear")
        print("Please wait...")

        bash.expect("Option:")
        bash.sendline("3")

        bash.expect("Confirm OpenVPN removal")
        bash.sendline("y")

        bash.expect("OpenVPN removed!")
        print(
            Fore.GREEN
            + "OV-Node uninstallation completed successfully!"
            + Style.RESET_ALL
        )
        deactivate_ovnode()
        input("Press Enter to return to the menu...")
        menu()

    except Exception as e:
        print(
            Fore.RED
            + "Error occurred during uninstallation: "
            + str(e)
            + Style.RESET_ALL
        )
        input("Press Enter to return to the menu...")
        menu()


def run_ovnode() -> None:
    """Create and run a systemd service for OV-Node"""
    service_content = """
[Unit]
Description=OV-Node App
After=network.target

[Service]
User=root
WorkingDirectory=/opt/ov-node/core
ExecStart=/opt/ov-node/venv/bin/python app.py
Restart=always
RestartSec=5
Environment="PATH=/opt/ov-node/venv/bin:/usr/local/bin:/usr/bin:/bin"

[Install]
WantedBy=multi-user.target
"""

    with open("/etc/systemd/system/ov-node.service", "w") as f:
        f.write(service_content)

    subprocess.run(["sudo", "systemctl", "daemon-reload"])
    subprocess.run(["sudo", "systemctl", "enable", "ov-node"])
    subprocess.run(["sudo", "systemctl", "start", "ov-node"])


def deactivate_ovnode() -> None:
    """Stop and disable the OV-Node systemd service"""
    subprocess.run(["sudo", "systemctl", "stop", "ov-node"])
    subprocess.run(["sudo", "systemctl", "disable", "ov-node"])
    subprocess.run(["rm", "-f", "/etc/systemd/system/ov-node.service"])


def menu():
    subprocess.run("clear")
    print(Fore.BLUE + "=" * 34)
    print("Welcome to the OV-Node Installer")
    print("=" * 34 + Style.RESET_ALL)
    print()
    print("Please choose an option:\n")
    print("  1. Install OV-Node")
    print("  2. Update OV-Node")
    print("  3. Uninstall OV-Node")
    print("  4. Exit")
    print()
    choice = input(Fore.YELLOW + "Enter your choice: " + Style.RESET_ALL)

    if choice == "1":
        install_ovnode()
    elif choice == "2":
        update_ovnode()
    elif choice == "3":
        uninstall_ovnode()
    elif choice == "4":
        print(Fore.GREEN + "\nExiting..." + Style.RESET_ALL)
        sys.exit()
    else:
        print(Fore.RED + "\nInvalid choice. Please try again." + Style.RESET_ALL)
        input(Fore.YELLOW + "Press Enter to continue..." + Style.RESET_ALL)
        menu()


if __name__ == "__main__":
    menu()

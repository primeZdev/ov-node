import os
import pexpect, sys
import subprocess
import shutil
import requests
from uuid import uuid4
from colorama import Fore, Style


def install_ovnode():
    try:
        subprocess.run(
            ["wget", "https://git.io/vpn", "-O", "/root/openvpn-install.sh"], check=True
        )  # thanks to Nyr for ovpn installation script <3 https://github.com/Nyr/openvpn-install

        bash = pexpect.spawn(
            "bash /root/openvpn-install.sh", encoding="utf-8", timeout=300
        )
        subprocess.run("clear")
        print("Please wait while the prerequisites are installed...")

        bash.expect("Which IPv4 address should be used")
        bash.sendline("1")

        bash.expect("Which protocol should OpenVPN use")
        bash.sendline("2")

        bash.expect("What port should OpenVPN listen on")
        bash.sendline("1194")

        bash.expect("Select a DNS server for the clients")
        bash.sendline("1")

        bash.expect("Enter a name for the first client")
        bash.sendline("first_client")

        bash.expect("Press any key to continue")
        bash.sendline("")

        bash.expect("Finished!")
        bash.expect(pexpect.EOF)
        subprocess.run("clear")

        shutil.copy(".env.example", ".env")
        example_uuid = str(uuid4())
        service_port = input("Enter the service port (default 9090): ") or "9090"
        api_key = (
            input(f"Enter the API key (example: {example_uuid}): ") or example_uuid
        )

        with open(".env", "w") as f:
            f.write(f"SERVICE_PORT={service_port}\n")
            f.write(f"API_KEY={api_key}\n")

        subprocess.run(["pip", "install", "-r", "requirements.txt"], check=True)

        run_ovnode()
        input(
            Fore.GREEN
            + "Installation completed successfully! Press Enter to return to the menu..."
            + Style.RESET_ALL
        )
        menu()

    except Exception as e:
        print(
            Fore.RED + "Error occurred during installation: " + str(e) + Style.RESET_ALL
        )
        input("Press Enter to return to the menu...")
        menu()


def update_ovnode():
    try:
        repo = "https://api.github.com/repos/primeZdev/ov-node/releases/latest"
        install_dir = "/opt/ov-node"
        env_file = os.path.join(install_dir, ".env")
        backup_env = "/tmp/ovnode_env_backup"

        response = requests.get(repo)
        response.raise_for_status()
        release = response.json()

        download_url = release["tarball_url"]
        filename = "/tmp/ov-node-latest.tar.gz"

        print(Fore.YELLOW + f"Downloading {download_url}" + Style.RESET_ALL)
        subprocess.run(["wget", "-O", filename, download_url], check=True)

        if os.path.exists(env_file):
            shutil.copy2(env_file, backup_env)

        if os.path.exists(install_dir):
            shutil.rmtree(install_dir)

        os.makedirs(install_dir, exist_ok=True)

        subprocess.run(
            ["tar", "-xzf", filename, "-C", install_dir, "--strip-components=1"],
            check=True,
        )

        if os.path.exists(backup_env):
            shutil.move(backup_env, env_file)

        print(Fore.YELLOW + "Installing requirements..." + Style.RESET_ALL)
        os.chdir(install_dir)
        subprocess.run(["pip", "install", "-r", "requirements.txt"], check=True)

        subprocess.run(["systemctl", "restart", "ov-node"], check=True)

        print(Fore.GREEN + "OV-Node updated successfully!" + Style.RESET_ALL)
        input("Press Enter to return to the menu...")
        menu()

    except Exception as e:
        print(Fore.RED + f"Update failed: {e}" + Style.RESET_ALL)


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
ExecStart=/usr/bin/python3 app.py
Restart=always
RestartSec=5
Environment="PATH=/usr/local/bin:/usr/bin:/bin"

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

import pexpect
import re

from core.logger import logger
from core.schema.all_schemas import SetSettingsModel


def change_config(request: SetSettingsModel) -> bool:
    setting_file = "/etc/openvpn/server/server.conf"
    template_file = "/etc/openvpn/server/client-common.txt"
    try:
        with open(setting_file, "r") as file:
            config = file.read()
        config = re.sub(
            r"^port\s+\d+", f"port {request.ovpn_port}", config, flags=re.MULTILINE
        )
        config = re.sub(
            r"^proto\s+\w+",
            f"proto {request.protocol}",
            config,
            flags=re.MULTILINE,
        )

        with open(setting_file, "w") as file:
            file.write(config)

        # Update the client template
        with open(template_file, "r") as file:
            template = file.read()
        if request.tunnel_address and request.tunnel_address.strip() != "":
            # Update both address and port
            template = re.sub(
                r"^remote\s+\S+\s+\d+",
                f"remote {request.tunnel_address} {request.ovpn_port}",
                template,
                flags=re.MULTILINE,
            )
        else:
            template = re.sub(
                r"^remote\s+(\S+)\s+\d+",
                rf"remote \1 {request.ovpn_port}",
                template,
                flags=re.MULTILINE,
            )

        template = re.sub(
            r"^proto\s+\w+",
            f"proto {request.protocol}",
            template,
            flags=re.MULTILINE,
        )
        with open(template_file, "w") as file:
            file.write(template)

        restart_openvpn()
        logger.info(
            f"OpenVPN port changed to {request.ovpn_port}, protocol to {request.protocol}, and tunnel address to {request.tunnel_address}"
        )
        return True
    except Exception as e:
        logger.error(f"Error changing OpenVPN settings: {e}")
        return False


def restart_openvpn() -> None:
    """Restart the OpenVPN service with systemctl"""
    try:
        logger.info("Restarting OpenVPN service...")
        import subprocess

        subprocess.run(
            ["/usr/bin/systemctl", "restart", "openvpn-server@server"],
            check=True,
            timeout=30,
        )
        logger.info("OpenVPN service restarted successfully.")
    except subprocess.TimeoutExpired:
        logger.error("Timeout while restarting OpenVPN service")
    except Exception as e:
        logger.error(f"Error restarting OpenVPN service: {e}")

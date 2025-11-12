import pexpect
import re
import subprocess

from logger import logger
from schema.all_schemas import SetSettingsModel


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
        config = re.sub(
            r"^local\s+.*",
            f"local {request.tunnel_address}",
            config,
            flags=re.MULTILINE,
        )

        with open(setting_file, "w") as file:
            file.write(config)

        # Update the client template
        with open(template_file, "r") as file:
            template = file.read()
        
        # Replace remote line - handle multiple formats:
        # "remote <ip> <port>", "remote  <port>", or "remote <port>"
        remote_pattern = r"^remote\s+.*$"
        template = re.sub(
            remote_pattern,
            f"remote {request.tunnel_address} {request.ovpn_port}",
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
        # Use subprocess instead of pexpect for better reliability
        result = subprocess.run(
            ["systemctl", "restart", "openvpn-server@server"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            logger.info("OpenVPN service restarted successfully.")
        else:
            logger.error(f"Failed to restart OpenVPN: {result.stderr}")
    except Exception as e:
        logger.error(f"Error restarting OpenVPN service: {e}")


def get_public_ip() -> str:
    """Get the public IP address of the server"""
    try:
        # Try multiple services for redundancy
        result = subprocess.run(
            ["curl", "-s", "-4", "ifconfig.me"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        
        # Fallback
        result = subprocess.run(
            ["curl", "-s", "-4", "icanhazip.com"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
            
        logger.warning("Could not get public IP, using localhost")
        return "127.0.0.1"
    except Exception as e:
        logger.error(f"Error getting public IP: {e}")
        return "127.0.0.1"


def fix_openvpn_template() -> bool:
    """Fix the OpenVPN client template if it has missing IP address"""
    template_file = "/etc/openvpn/server/client-common.txt"
    try:
        import os
        if not os.path.exists(template_file):
            logger.warning(f"Template file {template_file} does not exist")
            return False
            
        with open(template_file, "r") as file:
            template = file.read()
        
        # Check if remote line is missing IP (has format "remote  <port>" or "remote <port>")
        if re.search(r"^remote\s+\d+$", template, re.MULTILINE) or \
           re.search(r"^remote\s{2,}\d+$", template, re.MULTILINE):
            logger.warning("OpenVPN template has missing IP address, fixing...")
            
            # Get public IP
            public_ip = get_public_ip()
            
            # Extract current port from template
            port_match = re.search(r"^remote\s+(\d+)$", template, re.MULTILINE)
            if not port_match:
                port_match = re.search(r"^remote\s{2,}(\d+)$", template, re.MULTILINE)
            
            port = port_match.group(1) if port_match else "1194"
            
            # Fix the remote line
            template = re.sub(
                r"^remote\s+.*$",
                f"remote {public_ip} {port}",
                template,
                flags=re.MULTILINE
            )
            
            with open(template_file, "w") as file:
                file.write(template)
            
            logger.info(f"Fixed OpenVPN template with IP: {public_ip} and port: {port}")
            return True
        else:
            logger.info("OpenVPN template is already correctly configured")
            return True
            
    except Exception as e:
        logger.error(f"Error fixing OpenVPN template: {e}")
        return False


def fix_openvpn_server_config() -> bool:
    """Fix the OpenVPN server config if it has missing local IP address or other critical settings"""
    config_file = "/etc/openvpn/server/server.conf"
    try:
        import os
        if not os.path.exists(config_file):
            logger.error(f"Config file {config_file} does not exist")
            return False
            
        with open(config_file, "r") as file:
            config = file.read()
        
        config_modified = False
        
        # Fix 1: Check if local directive is missing IP
        if re.search(r"^local\s*$", config, re.MULTILINE):
            logger.warning("OpenVPN server config has missing local IP address, fixing...")
            
            # Get server IP addresses
            result = subprocess.run(
                ["ip", "addr", "show"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Extract public IP addresses (excluding loopback and VPN)
                ips = []
                for line in result.stdout.split("\n"):
                    match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', line)
                    if match:
                        ip = match.group(1)
                        if not ip.startswith("127.") and not ip.startswith("10.8."):
                            ips.append(ip)
                
                if ips:
                    selected_ip = ips[0]  # Use first available IP
                    logger.info(f"Selected IP address for OpenVPN: {selected_ip}")
                    
                    # Fix the local line
                    config = re.sub(
                        r"^local\s*$",
                        f"local {selected_ip}",
                        config,
                        flags=re.MULTILINE
                    )
                    config_modified = True
                    logger.info(f"Fixed 'local' directive with IP: {selected_ip}")
        
        # Fix 2: Check if 'port' is missing
        if not re.search(r"^port\s+\d+", config, re.MULTILINE):
            logger.warning("Missing 'port' directive, adding default port 1194")
            # Add port directive after local
            if re.search(r"^local\s+", config, re.MULTILINE):
                config = re.sub(
                    r"(^local\s+.+)$",
                    r"\1\nport 1194",
                    config,
                    flags=re.MULTILINE
                )
            else:
                # Add at beginning
                config = "port 1194\n" + config
            config_modified = True
            logger.info("Added 'port 1194' directive")
        
        # Fix 3: Check if 'proto' is missing
        if not re.search(r"^proto\s+\w+", config, re.MULTILINE):
            logger.warning("Missing 'proto' directive, adding default proto udp")
            # Add proto directive after port
            if re.search(r"^port\s+", config, re.MULTILINE):
                config = re.sub(
                    r"(^port\s+\d+)$",
                    r"\1\nproto udp",
                    config,
                    flags=re.MULTILINE
                )
            else:
                config = "proto udp\n" + config
            config_modified = True
            logger.info("Added 'proto udp' directive")
        
        # Fix 4: Check if 'dev tun' is missing (CRITICAL)
        if not re.search(r"^dev\s+tun", config, re.MULTILINE):
            logger.warning("Missing 'dev tun' directive, adding it")
            # Add dev tun after proto
            if re.search(r"^proto\s+", config, re.MULTILINE):
                config = re.sub(
                    r"(^proto\s+\w+)$",
                    r"\1\ndev tun",
                    config,
                    flags=re.MULTILINE
                )
            else:
                config = "dev tun\n" + config
            config_modified = True
            logger.info("Added 'dev tun' directive")
        
        # Write back if modified
        if config_modified:
            with open(config_file, "w") as file:
                file.write(config)
            logger.info("OpenVPN server config has been fixed and saved")
            return True
        else:
            logger.info("OpenVPN server config is already correctly configured")
            return True
            
    except Exception as e:
        logger.error(f"Error fixing OpenVPN server config: {e}")
        return False


def ensure_openvpn_running() -> bool:
    """
    Ensure OpenVPN service is running correctly.
    This function will:
    1. Check if config has errors and fix them
    2. Enable the service if not enabled
    3. Start/restart the service
    4. Verify it's running and port is open
    """
    try:
        logger.info("Ensuring OpenVPN service is running...")
        
        # Step 1: Fix any config issues
        logger.info("Checking and fixing configuration files...")
        fix_openvpn_server_config()
        fix_openvpn_template()
        
        # Step 2: Check if service is enabled, if not enable it
        enabled_check = subprocess.run(
            ["systemctl", "is-enabled", "openvpn-server@server"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if enabled_check.returncode != 0:
            logger.info("Enabling OpenVPN service...")
            subprocess.run(
                ["systemctl", "enable", "openvpn-server@server"],
                capture_output=True,
                text=True,
                timeout=10
            )
        
        # Step 3: Restart the service
        logger.info("Restarting OpenVPN service...")
        restart_result = subprocess.run(
            ["systemctl", "restart", "openvpn-server@server"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if restart_result.returncode != 0:
            logger.error(f"Failed to restart OpenVPN: {restart_result.stderr}")
            # Get detailed error from journalctl
            logs = subprocess.run(
                ["journalctl", "-u", "openvpn-server@server", "-n", "20", "--no-pager"],
                capture_output=True,
                text=True,
                timeout=10
            )
            logger.error(f"Recent logs:\n{logs.stdout}")
            return False
        
        # Step 4: Wait a bit for service to fully start
        import time
        time.sleep(3)
        
        # Step 5: Verify service is running
        status_check = subprocess.run(
            ["systemctl", "is-active", "openvpn-server@server"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        is_running = status_check.returncode == 0
        
        if is_running:
            logger.info("✓ OpenVPN service is running successfully")
            
            # Step 6: Check if port is open
            # Read config to get port and protocol
            with open("/etc/openvpn/server/server.conf", "r") as f:
                config = f.read()
            
            port = "1194"  # default
            protocol = "udp"  # default
            
            port_match = re.search(r"^port\s+(\d+)", config, re.MULTILINE)
            if port_match:
                port = port_match.group(1)
            
            proto_match = re.search(r"^proto\s+(\w+)", config, re.MULTILINE)
            if proto_match:
                protocol = proto_match.group(1)
            
            # Check if port is listening
            if protocol == "udp":
                port_check = subprocess.run(
                    ["ss", "-ulnp"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            else:
                port_check = subprocess.run(
                    ["ss", "-tlnp"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            
            if f":{port}" in port_check.stdout:
                logger.info(f"✓ OpenVPN is listening on port {port}/{protocol}")
                return True
            else:
                logger.warning(f"⚠ OpenVPN service is running but port {port}/{protocol} is not open")
                return True  # Service is running, port issue might resolve itself
        else:
            logger.error("✗ OpenVPN service failed to start")
            # Get error logs
            logs = subprocess.run(
                ["journalctl", "-u", "openvpn-server@server", "-n", "30", "--no-pager"],
                capture_output=True,
                text=True,
                timeout=10
            )
            logger.error(f"Error logs:\n{logs.stdout}")
            return False
            
    except Exception as e:
        logger.error(f"Error ensuring OpenVPN is running: {e}")
        return False



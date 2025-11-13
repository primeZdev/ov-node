"""
OpenVPN Service Monitor and Auto-Fix Module
This module monitors OpenVPN service health and automatically fixes configuration issues.
"""

import subprocess
import re
import os
import time
from typing import Dict, List, Optional, Tuple

from logger import logger


class OpenVPNMonitor:
    """Monitor and maintain OpenVPN service health"""
    
    def __init__(self):
        self.config_file = "/etc/openvpn/server/server.conf"
        self.template_file = "/etc/openvpn/server/client-common.txt"
        self.service_name = "openvpn-server@server"
        
    def check_service_status(self) -> Dict[str, any]:
        """
        Check the current status of OpenVPN service
        
        Returns:
            Dict with status information
        """
        result = {
            "running": False,
            "enabled": False,
            "active_state": "unknown",
            "error": None
        }
        
        try:
            # Check if service is active
            status_result = subprocess.run(
                ["systemctl", "is-active", self.service_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            result["active_state"] = status_result.stdout.strip()
            result["running"] = status_result.returncode == 0
            
            # Check if service is enabled
            enabled_result = subprocess.run(
                ["systemctl", "is-enabled", self.service_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            result["enabled"] = enabled_result.returncode == 0
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Error checking service status: {e}")
            
        return result
    
    def get_service_logs(self, lines: int = 20) -> List[str]:
        """
        Get recent service logs
        
        Args:
            lines: Number of log lines to retrieve
            
        Returns:
            List of log lines
        """
        try:
            result = subprocess.run(
                ["journalctl", "-u", self.service_name, "-n", str(lines), "--no-pager"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return result.stdout.strip().split("\n")
            return []
            
        except Exception as e:
            logger.error(f"Error getting service logs: {e}")
            return []
    
    def detect_config_errors(self) -> List[Dict[str, str]]:
        """
        Detect configuration errors by analyzing logs and config files
        
        Returns:
            List of detected errors with details
        """
        errors = []
        
        # Check logs for errors
        logs = self.get_service_logs(50)
        for log in logs:
            # Check for "local" option error (missing IP)
            if "Options error" in log and "local" in log:
                errors.append({
                    "type": "missing_local_ip",
                    "severity": "critical",
                    "message": "Missing IP address in 'local' directive",
                    "log": log
                })
            
            # Check for unrecognized options
            if "Unrecognized option" in log:
                errors.append({
                    "type": "unrecognized_option",
                    "severity": "critical",
                    "message": "Configuration contains unrecognized options",
                    "log": log
                })
            
            # Check for port binding issues
            if "bind" in log.lower() and "failed" in log.lower():
                errors.append({
                    "type": "port_binding",
                    "severity": "critical",
                    "message": "Failed to bind to port",
                    "log": log
                })
                
        return errors
    
    def get_server_ip_addresses(self) -> List[str]:
        """
        Get all IP addresses of the server
        
        Returns:
            List of IP addresses
        """
        ips = []
        try:
            result = subprocess.run(
                ["ip", "addr", "show"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Extract IPv4 addresses (excluding loopback)
                for line in result.stdout.split("\n"):
                    match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', line)
                    if match:
                        ip = match.group(1)
                        if not ip.startswith("127.") and not ip.startswith("10.8."):
                            ips.append(ip)
                            
        except Exception as e:
            logger.error(f"Error getting server IPs: {e}")
            
        return ips
    
    def get_public_ip(self) -> Optional[str]:
        """
        Get the public IP address of the server
        
        Returns:
            Public IP address or None
        """
        try:
            # Try multiple services
            services = [
                ["curl", "-s", "-4", "ifconfig.me"],
                ["curl", "-s", "-4", "icanhazip.com"],
                ["curl", "-s", "-4", "api.ipify.org"]
            ]
            
            for service in services:
                try:
                    result = subprocess.run(
                        service,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        ip = result.stdout.strip()
                        # Validate IP format
                        if re.match(r'^\d+\.\d+\.\d+\.\d+$', ip):
                            return ip
                except:
                    continue
                    
        except Exception as e:
            logger.error(f"Error getting public IP: {e}")
            
        return None
    
    def fix_missing_local_ip(self) -> bool:
        """
        Fix missing IP address in 'local' directive
        
        Returns:
            True if fixed successfully, False otherwise
        """
        try:
            if not os.path.exists(self.config_file):
                logger.error(f"Config file not found: {self.config_file}")
                return False
            
            # Read config
            with open(self.config_file, "r") as f:
                config = f.read()
            
            # Check if local directive is missing IP
            if re.search(r'^local\s*$', config, re.MULTILINE):
                logger.warning("Detected 'local' directive without IP address")
                
                # Get server IPs
                ips = self.get_server_ip_addresses()
                if not ips:
                    logger.error("No valid IP addresses found on server")
                    return False
                
                # Use first public IP (or first IP if no public IP found)
                selected_ip = ips[0]
                logger.info(f"Selected IP address: {selected_ip}")
                
                # Fix the config
                config = re.sub(
                    r'^local\s*$',
                    f'local {selected_ip}',
                    config,
                    flags=re.MULTILINE
                )
                
                # Write back
                with open(self.config_file, "w") as f:
                    f.write(config)
                
                logger.info(f"Fixed 'local' directive with IP: {selected_ip}")
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"Error fixing missing local IP: {e}")
            return False
    
    def validate_config_syntax(self) -> Tuple[bool, Optional[str]]:
        """
        Validate OpenVPN config syntax
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check if openvpn binary exists
            openvpn_path = None
            for path in ["/usr/sbin/openvpn", "/usr/bin/openvpn", "/sbin/openvpn"]:
                if os.path.exists(path):
                    openvpn_path = path
                    break
            
            if not openvpn_path:
                # OpenVPN binary not found, skip validation
                logger.debug("OpenVPN binary not found, skipping syntax validation")
                return True, None
            
            result = subprocess.run(
                [openvpn_path, "--config", self.config_file, "--test-crypto"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return False, result.stderr
            
            return True, None
            
        except FileNotFoundError:
            # OpenVPN command not found, but that's ok
            logger.debug("OpenVPN command not found for validation")
            return True, None
        except Exception as e:
            logger.warning(f"Config syntax validation skipped: {e}")
            return True, None
    
    def check_port_listening(self, port: int = 1194, protocol: str = "udp") -> bool:
        """
        Check if OpenVPN is listening on the configured port
        
        Args:
            port: Port number to check
            protocol: Protocol (tcp/udp)
            
        Returns:
            True if listening, False otherwise
        """
        try:
            if protocol == "udp":
                result = subprocess.run(
                    ["ss", "-ulnp"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            else:
                result = subprocess.run(
                    ["ss", "-tlnp"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            
            if result.returncode == 0:
                # Check if port is in the output
                return f":{port}" in result.stdout
                
        except Exception as e:
            logger.error(f"Error checking port listening: {e}")
            
        return False
    
    def get_config_port_protocol(self) -> Tuple[int, str]:
        """
        Get port and protocol from config file
        
        Returns:
            Tuple of (port, protocol)
        """
        port = 1194  # default
        protocol = "udp"  # default
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r") as f:
                    config = f.read()
                
                # Extract port
                port_match = re.search(r'^port\s+(\d+)', config, re.MULTILINE)
                if port_match:
                    port = int(port_match.group(1))
                
                # Extract protocol
                proto_match = re.search(r'^proto\s+(\w+)', config, re.MULTILINE)
                if proto_match:
                    protocol = proto_match.group(1)
                    
        except Exception as e:
            logger.error(f"Error reading config port/protocol: {e}")
            
        return port, protocol
    
    def restart_service(self) -> bool:
        """
        Restart OpenVPN service
        
        Returns:
            True if restarted successfully, False otherwise
        """
        try:
            logger.info(f"Restarting {self.service_name}...")
            result = subprocess.run(
                ["systemctl", "restart", self.service_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info("Service restarted successfully")
                # Wait a bit for service to fully start
                time.sleep(2)
                return True
            else:
                logger.error(f"Failed to restart service: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error restarting service: {e}")
            return False
    
    def enable_service(self) -> bool:
        """
        Enable OpenVPN service to start on boot
        
        Returns:
            True if enabled successfully, False otherwise
        """
        try:
            result = subprocess.run(
                ["systemctl", "enable", self.service_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logger.info("Service enabled successfully")
                return True
            else:
                logger.error(f"Failed to enable service: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error enabling service: {e}")
            return False
    
    def auto_fix_and_restart(self) -> Dict[str, any]:
        """
        Automatically detect and fix configuration issues, then restart service
        
        Returns:
            Dict with fix results
        """
        result = {
            "success": False,
            "errors_detected": [],
            "fixes_applied": [],
            "service_running": False,
            "port_open": False
        }
        
        logger.info("Starting OpenVPN auto-fix procedure...")
        
        # 1. Check current status
        status = self.check_service_status()
        logger.info(f"Current service status: {status}")
        
        # 2. Detect errors
        errors = self.detect_config_errors()
        result["errors_detected"] = errors
        
        if errors:
            logger.warning(f"Detected {len(errors)} configuration errors")
            
            # 3. Apply fixes
            for error in errors:
                if error["type"] == "missing_local_ip":
                    if self.fix_missing_local_ip():
                        result["fixes_applied"].append("fixed_missing_local_ip")
                        logger.info("Fixed missing local IP")
        
        # 4. Ensure service is enabled
        if not status["enabled"]:
            if self.enable_service():
                result["fixes_applied"].append("enabled_service")
        
        # 5. Restart service
        if self.restart_service():
            result["fixes_applied"].append("restarted_service")
            
            # 6. Verify service is running
            time.sleep(3)
            new_status = self.check_service_status()
            result["service_running"] = new_status["running"]
            
            # 7. Check if port is open
            port, protocol = self.get_config_port_protocol()
            result["port_open"] = self.check_port_listening(port, protocol)
            result["success"] = result["service_running"] and result["port_open"]
            
            if result["success"]:
                logger.info("OpenVPN service is now running correctly")
            else:
                logger.warning("Service started but issues remain")
                if not result["port_open"]:
                    logger.warning(f"Port {port}/{protocol} is not open")
        else:
            logger.error("Failed to restart service")
        
        return result
    
    def health_check(self) -> Dict[str, any]:
        """
        Perform comprehensive health check
        
        Returns:
            Dict with health status
        """
        health = {
            "healthy": False,
            "service_running": False,
            "port_listening": False,
            "config_valid": False,
            "issues": []
        }
        
        # Check service status
        status = self.check_service_status()
        health["service_running"] = status["running"]
        
        if not status["running"]:
            health["issues"].append("Service is not running")
        
        if not status["enabled"]:
            health["issues"].append("Service is not enabled on boot")
        
        # Check port
        port, protocol = self.get_config_port_protocol()
        health["port_listening"] = self.check_port_listening(port, protocol)
        
        if not health["port_listening"]:
            health["issues"].append(f"Port {port}/{protocol} is not listening")
        
        # Check config
        is_valid, error = self.validate_config_syntax()
        health["config_valid"] = is_valid
        
        if not is_valid:
            health["issues"].append(f"Config validation failed: {error}")
        
        # Overall health
        health["healthy"] = (
            health["service_running"] and 
            health["port_listening"] and 
            health["config_valid"]
        )
        
        return health


# Global instance
openvpn_monitor = OpenVPNMonitor()


def check_and_fix_openvpn_service() -> Dict[str, any]:
    """
    Convenience function to check and fix OpenVPN service
    
    Returns:
        Dict with results
    """
    return openvpn_monitor.auto_fix_and_restart()


def get_openvpn_health() -> Dict[str, any]:
    """
    Convenience function to get OpenVPN health status
    
    Returns:
        Dict with health status
    """
    return openvpn_monitor.health_check()

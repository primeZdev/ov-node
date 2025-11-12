import pexpect
import re
import os
import subprocess

from logger import logger


script_path = "/root/openvpn-install.sh"


def validate_and_fix_ovpn_file(ovpn_file: str) -> bool:
    """
    Validate that .ovpn file has correct remote IP address
    If missing, fix it by getting the public IP
    
    Args:
        ovpn_file: Path to .ovpn file
        
    Returns:
        True if file is valid or fixed successfully, False otherwise
    """
    try:
        with open(ovpn_file, 'r') as f:
            content = f.read()
        
        # Check if remote line is missing IP (format: "remote  1194" or "remote 1194")
        if re.search(r'^remote\s+\d+$', content, re.MULTILINE) or \
           re.search(r'^remote\s{2,}\d+$', content, re.MULTILINE):
            logger.warning(f"OVPN file {ovpn_file} has missing IP in remote directive, fixing...")
            
            # Get public IP
            public_ip = None
            try:
                result = subprocess.run(
                    ["curl", "-s", "-4", "ifconfig.me"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0 and result.stdout.strip():
                    public_ip = result.stdout.strip()
            except:
                pass
            
            if not public_ip:
                # Try to get from server IP
                result = subprocess.run(
                    ["ip", "addr", "show"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.split("\n"):
                        match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', line)
                        if match:
                            ip = match.group(1)
                            if not ip.startswith("127.") and not ip.startswith("10.8."):
                                public_ip = ip
                                break
            
            if not public_ip:
                logger.error("Cannot get public IP to fix OVPN file")
                return False
            
            # Extract port from remote line
            port_match = re.search(r'^remote\s+(\d+)$', content, re.MULTILINE)
            if not port_match:
                port_match = re.search(r'^remote\s{2,}(\d+)$', content, re.MULTILINE)
            
            port = port_match.group(1) if port_match else "1194"
            
            # Fix the remote line
            content = re.sub(
                r'^remote\s+.*$',
                f'remote {public_ip} {port}',
                content,
                flags=re.MULTILINE
            )
            
            # Write back
            with open(ovpn_file, 'w') as f:
                f.write(content)
            
            logger.info(f"Fixed OVPN file {ovpn_file} with IP: {public_ip} and port: {port}")
            return True
        else:
            # Check if remote line has valid IP
            remote_match = re.search(r'^remote\s+(\d+\.\d+\.\d+\.\d+)\s+\d+', content, re.MULTILINE)
            if remote_match:
                logger.info(f"OVPN file {ovpn_file} has valid remote directive")
                return True
            else:
                logger.error(f"OVPN file {ovpn_file} has invalid remote directive format")
                return False
                
    except Exception as e:
        logger.error(f"Error validating OVPN file {ovpn_file}: {e}")
        return False


def create_user_on_server(name, expiry_date=None) -> bool:
    try:
        # Ensure OpenVPN template is fixed before creating user
        from setting.core import fix_openvpn_template, fix_openvpn_server_config
        logger.info("Ensuring OpenVPN configuration is correct before creating user...")
        fix_openvpn_server_config()
        fix_openvpn_template()
        
        # Validate input name
        if not name or not name.strip():
            logger.error("Invalid user name: name cannot be empty")
            return False
        
        # Check if client already exists
        cert_path = f"/etc/openvpn/server/easy-rsa/pki/issued/{name}.crt"
        if os.path.exists(cert_path):
            logger.warning(f"User '{name}' already exists")
            # Check if .ovpn file exists, if yes, consider it success
            ovpn_path = f"/root/{name}.ovpn"
            if os.path.exists(ovpn_path):
                logger.info(f"User '{name}' already exists with valid .ovpn file")
                return True
            else:
                logger.error(f"User '{name}' exists but .ovpn file is missing")
                return False
        
        if not os.path.exists(script_path):
            logger.error("script not found on ")
            return False

        env = {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"}
        bash = pexpect.spawn(
            "/usr/bin/bash",
            [script_path],
            env=env,
            encoding="utf-8",
            timeout=120,
        )

        bash.expect(r"Option:", timeout=90)
        bash.sendline("1")

        # Wait for name prompt - could be first prompt or repeated if invalid
        index = bash.expect([r"Name:", r"invalid name"], timeout=90)
        bash.sendline(name)
        
        # Handle case where name might be invalid and script asks again
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            index = bash.expect([
                r"Name:",  # 0 - Script asking for name again (invalid/duplicate)
                r"added\. Configuration available",  # 1 - Success message
                pexpect.EOF,  # 2 - Script finished
                pexpect.TIMEOUT  # 3 - Timeout
            ], timeout=180)
            
            if index == 0:
                # Script is asking for name again - means duplicate or invalid
                logger.error(f"User name '{name}' is invalid or already exists in script")
                bash.close(force=True)
                return False
            elif index == 1:
                # Success message found
                logger.info(f"User '{name}' created successfully")
                bash.expect(pexpect.EOF, timeout=10)
                bash.close()
                
                # Validate the generated .ovpn file
                ovpn_file = f"/root/{name}.ovpn"
                if os.path.exists(ovpn_file):
                    if validate_and_fix_ovpn_file(ovpn_file):
                        logger.info(f"OVPN file for '{name}' validated successfully")
                        return True
                    else:
                        logger.error(f"OVPN file for '{name}' validation failed")
                        return False
                else:
                    logger.error(f"OVPN file not found after creation: {ovpn_file}")
                    return False
            elif index == 2:
                # EOF - script finished
                logger.info(f"Script finished for user '{name}'")
                bash.close()
                return True
            
            retry_count += 1

        logger.error(f"Max retries reached for user '{name}'")
        bash.close(force=True)
        return False

    except pexpect.TIMEOUT as e:
        logger.error(f"Timeout occurred while executing script: {e}")
        try:
            bash.close(force=True)
        except:
            pass
        return False
    except pexpect.EOF as e:
        logger.error(f"Script closed earlier than expected: {e}")
        try:
            bash.close(force=True)
        except:
            pass
        return False
    except Exception as e:
        logger.error(f"Error occurred: {e}")
        try:
            bash.close(force=True)
        except:
            pass
        return False


def delete_user_on_server(name) -> bool | str:
    try:
        # Validate input
        if not name or not name.strip():
            logger.error("Invalid user name: name cannot be empty")
            return False
        
        if not os.path.exists(script_path):
            logger.error("script not found at %s", script_path)
            return False

        env = {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"}
        bash = pexpect.spawn(
            "/usr/bin/bash", [script_path], env=env, encoding="utf-8", timeout=120
        )

        try:
            bash.expect(r"Option:|Select an option:", timeout=20)
        except pexpect.TIMEOUT:
            logger.warning("Did not see main menu prompt, attempting to continue")

        bash.sendline("2")

        try:
            bash.expect(
                r"Select the client to revoke:|Select the client to revoke", timeout=20
            )
        except pexpect.TIMEOUT:
            logger.info("Didn't match full header")

        try:
            bash.expect(r"Client:", timeout=20)
            list_output = bash.before
        except pexpect.TIMEOUT:
            logger.error("Timeout waiting for client list")
            bash.close(force=True)
            return False

        pattern = re.compile(r"\s*(\d+)\)\s*(.+)")
        matches = pattern.findall(list_output)

        user_number = None
        for num, user in matches:
            if user.strip() == name:
                user_number = num
                break

        if not user_number:
            logger.error("User '%s' not found for delete!", name)
            bash.close(force=True)
            return "not_found"

        logger.info("Revoking user '%s' -> number %s", name, user_number)
        bash.sendline(user_number)

        try:
            bash.expect(
                r"Confirm .*revocation\?.*\[y/N\]:|Confirm .*revocation\?.*:|Confirm .*revocation\?",
                timeout=20,
            )
            bash.sendline("y")
        except pexpect.TIMEOUT:
            logger.warning("Confirmation prompt not seen; trying to continue")

        try:
            bash.expect(pexpect.EOF, timeout=120)
        except pexpect.TIMEOUT:
            logger.error("Timeout waiting for script to finish")
            bash.close(force=True)
            return False
            
        bash.close()

        # remove local .ovpn file if exists
        file_to_delete = f"/root/{name}.ovpn"
        if os.path.exists(file_to_delete):
            try:
                os.remove(file_to_delete)
                logger.info("Removed %s", file_to_delete)
            except Exception as e:
                logger.error("Error deleting file %s: %s", file_to_delete, e)
                return True

        return True

    except pexpect.TIMEOUT as e:
        logger.exception("Timeout in delete_user_on_server: %s", e)
        try:
            bash.close(force=True)
        except:
            pass
        return False
    except Exception as e:
        logger.exception("Error in delete_user_on_server: %s", e)
        try:
            bash.close(force=True)
        except:
            pass
        return False


async def download_ovpn_file(name: str) -> str | None:
    """This function returns the path of the ovpn file for downloading"""
    file_path = f"/root/{name}.ovpn"
    if os.path.exists(file_path):
        # Validate and fix the file before returning
        if validate_and_fix_ovpn_file(file_path):
            return file_path
        else:
            logger.error(f"OVPN file validation failed for {name}")
            return None
    else:
        # Try to create user if file doesn't exist
        success = create_user_on_server(name)
        if success and os.path.exists(file_path):
            return file_path
        else:
            logger.error(f"Failed to create or find OVPN file for {name}")
            return None

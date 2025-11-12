#!/usr/bin/env python3
"""
CLI tool for OpenVPN service management
Usage: python openvpn_cli.py [command]

Commands:
    status  - Show OpenVPN service status
    health  - Run health check
    fix     - Auto-detect and fix issues
    restart - Restart OpenVPN service
    logs    - Show recent logs
"""

import sys
import os
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from service.openvpn_monitor import openvpn_monitor
from logger import logger


def print_json(data):
    """Pretty print JSON data"""
    print(json.dumps(data, indent=2))


def cmd_status():
    """Show OpenVPN service status"""
    print("=" * 50)
    print("OpenVPN Service Status")
    print("=" * 50)
    
    status = openvpn_monitor.check_service_status()
    print(f"Running:      {status['running']}")
    print(f"Enabled:      {status['enabled']}")
    print(f"Active State: {status['active_state']}")
    
    if status['error']:
        print(f"Error:        {status['error']}")
    
    port, protocol = openvpn_monitor.get_config_port_protocol()
    port_open = openvpn_monitor.check_port_listening(port, protocol)
    
    print(f"\nPort:         {port}")
    print(f"Protocol:     {protocol}")
    print(f"Port Open:    {port_open}")
    print()


def cmd_health():
    """Run health check"""
    print("=" * 50)
    print("OpenVPN Health Check")
    print("=" * 50)
    
    health = openvpn_monitor.health_check()
    
    print(f"Overall Health: {'✓ HEALTHY' if health['healthy'] else '✗ UNHEALTHY'}")
    print()
    print(f"Service Running:   {'✓' if health['service_running'] else '✗'}")
    print(f"Port Listening:    {'✓' if health['port_listening'] else '✗'}")
    print(f"Config Valid:      {'✓' if health['config_valid'] else '✗'}")
    
    if health['issues']:
        print(f"\nIssues Found: {len(health['issues'])}")
        for i, issue in enumerate(health['issues'], 1):
            print(f"  {i}. {issue}")
    else:
        print("\nNo issues found!")
    print()


def cmd_fix():
    """Auto-detect and fix issues"""
    print("=" * 50)
    print("OpenVPN Auto-Fix")
    print("=" * 50)
    
    print("Detecting and fixing issues...\n")
    
    result = openvpn_monitor.auto_fix_and_restart()
    
    if result['errors_detected']:
        print(f"Errors Detected: {len(result['errors_detected'])}")
        for error in result['errors_detected']:
            print(f"  - {error['message']}")
        print()
    
    if result['fixes_applied']:
        print(f"Fixes Applied: {len(result['fixes_applied'])}")
        for fix in result['fixes_applied']:
            print(f"  - {fix}")
        print()
    
    print(f"Service Running: {'✓' if result['service_running'] else '✗'}")
    print(f"Port Open:       {'✓' if result['port_open'] else '✗'}")
    print()
    
    if result['success']:
        print("✓ SUCCESS: OpenVPN is now running correctly!")
    else:
        print("✗ FAILED: OpenVPN still has issues")
        print("Check logs for more details: journalctl -u openvpn-server@server -n 50")
    print()


def cmd_restart():
    """Restart OpenVPN service"""
    print("=" * 50)
    print("Restart OpenVPN Service")
    print("=" * 50)
    
    print("Restarting service...")
    success = openvpn_monitor.restart_service()
    
    if success:
        print("✓ Service restarted successfully!")
        
        # Check status after restart
        status = openvpn_monitor.check_service_status()
        if status['running']:
            print("✓ Service is running")
        else:
            print("✗ Service failed to start")
    else:
        print("✗ Failed to restart service")
    print()


def cmd_logs():
    """Show recent logs"""
    print("=" * 50)
    print("OpenVPN Recent Logs (Last 30 lines)")
    print("=" * 50)
    
    logs = openvpn_monitor.get_service_logs(30)
    
    for log in logs:
        print(log)
    print()


def cmd_errors():
    """Detect configuration errors"""
    print("=" * 50)
    print("OpenVPN Configuration Errors")
    print("=" * 50)
    
    errors = openvpn_monitor.detect_config_errors()
    
    if errors:
        print(f"Found {len(errors)} errors:\n")
        for i, error in enumerate(errors, 1):
            print(f"{i}. [{error['severity'].upper()}] {error['message']}")
            print(f"   Type: {error['type']}")
            if 'log' in error:
                print(f"   Log: {error['log'][:100]}...")
            print()
    else:
        print("No configuration errors detected!")
    print()


def cmd_help():
    """Show help message"""
    print(__doc__)


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        cmd_help()
        return
    
    command = sys.argv[1].lower()
    
    commands = {
        'status': cmd_status,
        'health': cmd_health,
        'fix': cmd_fix,
        'restart': cmd_restart,
        'logs': cmd_logs,
        'errors': cmd_errors,
        'help': cmd_help,
    }
    
    if command in commands:
        try:
            commands[command]()
        except Exception as e:
            print(f"Error: {e}")
            logger.error(f"CLI error: {e}")
            sys.exit(1)
    else:
        print(f"Unknown command: {command}")
        print("Use 'help' to see available commands")
        sys.exit(1)


if __name__ == "__main__":
    main()

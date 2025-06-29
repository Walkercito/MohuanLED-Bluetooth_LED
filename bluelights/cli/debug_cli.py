#!/usr/bin/env python3
"""
Debug CLI for BlueLights LED Controller - Diagnose and troubleshoot issues.
"""
import asyncio
import click
import json
import sys
import platform
import subprocess
from pathlib import Path
from typing import Optional

try:
    from .debug import get_debugger, enable_debug_mode
    from .manager import BJLEDInstance
    from .scanner import Scanner
    from .exceptions import BlueLightsException
except ImportError:
    # Fallback for development
    sys.path.append(str(Path(__file__).parent))
    from debug import get_debugger, enable_debug_mode
    from manager import BJLEDInstance
    from scanner import Scanner
    from exceptions import BlueLightsException


@click.group()
@click.option('--debug', is_flag=True, help='Enable verbose debug output')
@click.option('--export-report', is_flag=True, help='Export debug report after command')
@click.pass_context
def debug_cli(ctx, debug, export_report):
    """BlueLights Debug CLI - Diagnose and troubleshoot LED controller issues."""
    ctx.ensure_object(dict)
    
    if debug:
        ctx.obj['debugger'] = enable_debug_mode()
    else:
        ctx.obj['debugger'] = get_debugger()
    
    ctx.obj['export_report'] = export_report


@debug_cli.command()
@click.pass_context
async def system_check(ctx):
    """Comprehensive system and Bluetooth check."""
    debugger = ctx.obj['debugger']
    
    click.echo("🔍 Running comprehensive system check...\n")
    
    try:
        # Collect Bluetooth info
        bt_info = await debugger.collect_bluetooth_info()
        
        # System Information
        click.echo("📋 SYSTEM INFORMATION")
        click.echo("=" * 50)
        click.echo(f"Operating System: {bt_info.system}")
        click.echo(f"Platform: {bt_info.platform}")
        click.echo(f"Python Version: {bt_info.python_version}")
        click.echo(f"Bleak Version: {bt_info.bleak_version}")
        
        # Bluetooth Status
        click.echo(f"\n🔵 BLUETOOTH STATUS")
        click.echo("=" * 50)
        click.echo(f"Adapter Powered: {'✅ YES' if bt_info.adapter_powered else '❌ NO'}")
        
        if bt_info.service_status:
            click.echo(f"Service Status: {bt_info.service_status}")
        
        if bt_info.permissions:
            click.echo(f"Permissions: {bt_info.permissions}")
        
        # Adapter Information
        click.echo(f"\n📡 BLUETOOTH ADAPTERS ({len(bt_info.adapters)})")
        click.echo("=" * 50)
        
        for i, adapter in enumerate(bt_info.adapters):
            click.echo(f"Adapter {i+1}:")
            if adapter['status'] == 'working':
                click.echo(f"  Status: ✅ Working")
                click.echo(f"  Devices Found: {adapter['devices_found']}")
                if adapter['device_list']:
                    click.echo("  Sample Devices:")
                    for device in adapter['device_list'][:3]:
                        click.echo(f"    - {device['name']} ({device['address']})")
            else:
                click.echo(f"  Status: ❌ Error")
                click.echo(f"  Error: {adapter['error']}")
        
        # Diagnosis and Recommendations
        click.echo(f"\n💡 DIAGNOSIS & RECOMMENDATIONS")
        click.echo("=" * 50)
        
        if not bt_info.adapter_powered:
            click.echo("❌ Bluetooth adapter is not powered on")
            
            if bt_info.system.lower() == 'linux':
                click.echo("🔧 Try these commands:")
                click.echo("   sudo systemctl start bluetooth")
                click.echo("   sudo bluetoothctl power on")
                click.echo("   sudo rfkill unblock bluetooth")
            elif bt_info.system.lower() == 'windows':
                click.echo("🔧 Try:")
                click.echo("   - Check Windows Bluetooth settings")
                click.echo("   - Restart Bluetooth service in Services.msc")
            else:
                click.echo("🔧 Check your system's Bluetooth settings")
        else:
            click.echo("✅ Bluetooth appears to be working correctly")
        
        # Check for common issues
        if bt_info.system.lower() == 'linux':
            await _check_linux_specific_issues()
        
        click.echo(f"\n✅ System check completed!")
        
    except Exception as e:
        click.echo(f"❌ System check failed: {e}")
        debugger.log_error("system_check", e)
        
    finally:
        if ctx.obj['export_report']:
            report_path = debugger.export_debug_report()
            click.echo(f"\n📄 Debug report saved: {report_path}")


async def _check_linux_specific_issues():
    """Check for common Linux-specific Bluetooth issues."""
    click.echo(f"\n🐧 LINUX-SPECIFIC CHECKS")
    click.echo("=" * 50)
    
    # Check if user is in bluetooth group
    try:
        result = subprocess.run(['groups'], capture_output=True, text=True)
        groups = result.stdout.strip()
        
        if 'bluetooth' in groups:
            click.echo("✅ User is in 'bluetooth' group")
        else:
            click.echo("⚠️  User is NOT in 'bluetooth' group")
            click.echo("🔧 Add user to bluetooth group:")
            click.echo("   sudo usermod -a -G bluetooth $USER")
            click.echo("   Then log out and log back in")
    except:
        click.echo("❓ Could not check user groups")
    
    # Check bluetoothctl availability
    try:
        result = subprocess.run(['which', 'bluetoothctl'], capture_output=True)
        if result.returncode == 0:
            click.echo("✅ bluetoothctl is available")
        else:
            click.echo("❌ bluetoothctl not found")
            click.echo("🔧 Install bluez: sudo apt install bluez")
    except:
        click.echo("❓ Could not check bluetoothctl")


@debug_cli.command()
@click.option('--timeout', '-t', default=10.0, help='Scan timeout in seconds')
@click.option('--detailed', '-d', is_flag=True, help='Show detailed device information')
@click.pass_context
async def scan_devices(ctx, timeout, detailed):
    """Scan for available LED devices with detailed information."""
    debugger = ctx.obj['debugger']
    
    click.echo(f"🔍 Scanning for devices (timeout: {timeout}s)...\n")
    
    try:
        from bleak import BleakScanner
        
        # Perform scan
        devices = await asyncio.wait_for(
            BleakScanner.discover(timeout=timeout),
            timeout=timeout + 2.0
        )
        
        click.echo(f"📱 DISCOVERED DEVICES ({len(devices)})")
        click.echo("=" * 60)
        
        led_devices = []
        other_devices = []
        
        for device in devices:
            device_info = {
                'name': device.name or 'Unknown',
                'address': device.address,
                'rssi': getattr(device, 'rssi', None),
                'uuids': getattr(device, 'uuids', [])
            }
            
            # Check if it's likely an LED device
            is_led = any(keyword in device_info['name'].lower() 
                        for keyword in ['led', 'bj_led_m', 'light', 'strip'])
            
            if is_led:
                led_devices.append(device_info)
            else:
                other_devices.append(device_info)
        
        # Show LED devices first
        if led_devices:
            click.echo("🌈 POTENTIAL LED DEVICES:")
            for device in led_devices:
                click.echo(f"  ✨ {device['name']}")
                click.echo(f"     MAC: {device['address']}")
                if device['rssi']:
                    click.echo(f"     Signal: {device['rssi']} dBm")
                if detailed and device['uuids']:
                    click.echo(f"     UUIDs: {len(device['uuids'])} found")
                    for uuid in device['uuids'][:3]:  # Show first 3
                        click.echo(f"       - {uuid}")
                click.echo()
        
        # Show other devices if detailed mode
        if detailed and other_devices:
            click.echo("📱 OTHER BLUETOOTH DEVICES:")
            for device in other_devices[:10]:  # Limit to 10
                click.echo(f"  • {device['name']} ({device['address']})")
                if device['rssi']:
                    click.echo(f"    Signal: {device['rssi']} dBm")
            
            if len(other_devices) > 10:
                click.echo(f"  ... and {len(other_devices) - 10} more devices")
            click.echo()
        
        # Summary and recommendations
        click.echo("💡 RECOMMENDATIONS:")
        if led_devices:
            click.echo(f"✅ Found {len(led_devices)} potential LED device(s)")
            click.echo("🔧 To test connection, try:")
            for device in led_devices:
                click.echo(f"   bluelights debug test-device --mac {device['address']}")
        else:
            click.echo("❌ No LED devices found")
            click.echo("🔧 Make sure your LED device is:")
            click.echo("   - Powered on")
            click.echo("   - In pairing/discoverable mode")
            click.echo("   - Within range (< 10 meters)")
        
    except asyncio.TimeoutError:
        click.echo(f"❌ Scan timed out after {timeout} seconds")
        click.echo("🔧 Try increasing timeout with --timeout option")
    except Exception as e:
        click.echo(f"❌ Scan failed: {e}")
        debugger.log_error("device_scan", e)
    
    finally:
        if ctx.obj['export_report']:
            report_path = debugger.export_debug_report()
            click.echo(f"\n📄 Debug report saved: {report_path}")


@debug_cli.command()
@click.option('--mac', required=True, help='MAC address of the device to test')
@click.option('--uuid', help='Specific UUID to test (optional)')
@click.option('--quick', '-q', is_flag=True, help='Quick test only')
@click.pass_context
async def test_device(ctx, mac, uuid, quick):
    """Test connection and compatibility with a specific device."""
    debugger = ctx.obj['debugger']
    
    click.echo(f"🧪 Testing device: {mac}\n")
    
    try:
        # Collect device information
        if not quick:
            click.echo("📊 Collecting device information...")
            device_info = await debugger.collect_device_info(mac)
            
            click.echo(f"📱 DEVICE INFORMATION")
            click.echo("=" * 50)
            click.echo(f"MAC Address: {device_info.mac_address}")
            click.echo(f"Device Name: {device_info.device_name or 'Unknown'}")
            click.echo(f"Services: {len(device_info.services)}")
            click.echo(f"Characteristics: {len(device_info.characteristics)}")
            click.echo(f"Total UUIDs: {len(device_info.uuids)}")
            
            if device_info.last_error:
                click.echo(f"Last Error: {device_info.last_error}")
        
        # Test LED functionality
        click.echo(f"\n🔌 TESTING LED FUNCTIONALITY")
        click.echo("=" * 50)
        
        # Create LED instance
        if uuid:
            led = BJLEDInstance(address=mac, uuid=uuid)
            click.echo(f"Using provided UUID: {uuid}")
        else:
            led = BJLEDInstance(address=mac)
            click.echo("Will auto-discover UUID...")
        
        # Add debug callback
        connection_states = []
        def state_callback(state):
            connection_states.append(state.value)
            click.echo(f"  Connection state: {state.value}")
        
        led.add_state_change_callback(state_callback)
        
        # Test connection
        click.echo("🔗 Testing connection...")
        success = await led.initialize()
        
        if success:
            click.echo("✅ Connection successful!")
            
            # Test basic commands
            click.echo("\n⚡ Testing LED commands...")
            
            with debugger.command_timer("turn_on", b"69960201001"):
                await led.turn_on()
                click.echo("  ✅ Turn ON command sent")
            
            await asyncio.sleep(1)
            
            with debugger.command_timer("set_color_red"):
                await led.set_color_to_rgb(255, 0, 0)
                click.echo("  ✅ Red color command sent")
            
            await asyncio.sleep(1)
            
            with debugger.command_timer("turn_off"):
                await led.turn_off()
                click.echo("  ✅ Turn OFF command sent")
            
            click.echo("\n🎉 All tests passed! Device is compatible.")
            
            # Show performance info
            metrics = debugger.performance_metrics
            avg_time = metrics.get('avg_command_time', 0)
            click.echo(f"\n📊 Performance: Avg command time: {avg_time:.3f}s")
            
        else:
            click.echo("❌ Connection failed")
        
        await led.disconnect()
        
    except BlueLightsException as e:
        click.echo(f"❌ LED Error: {e}")
        click.echo(f"Error Code: {e.error_code}")
        
        # Provide specific troubleshooting
        if "BLUETOOTH_NOT_AVAILABLE" in str(e.error_code):
            click.echo("\n🔧 TROUBLESHOOTING:")
            click.echo("   Run: bluelights debug system-check")
        elif "DEVICE_NOT_FOUND" in str(e.error_code):
            click.echo("\n🔧 TROUBLESHOOTING:")
            click.echo("   - Check if device is powered on")
            click.echo("   - Check if MAC address is correct")
            click.echo("   - Run: bluelights debug scan-devices")
        
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}")
        debugger.log_error("device_test", e)
    
    finally:
        if ctx.obj['export_report']:
            report_path = debugger.export_debug_report()
            click.echo(f"\n📄 Debug report saved: {report_path}")


@debug_cli.command()
@click.option('--mac', help='MAC address of the device')
@click.option('--commands', '-c', default=5, help='Number of test commands to send')
@click.pass_context
async def stress_test(ctx, mac, commands):
    """Stress test the LED connection with multiple rapid commands."""
    debugger = ctx.obj['debugger']
    
    click.echo(f"⚡ Running stress test ({commands} commands)...\n")
    
    try:
        # Initialize LED
        if mac:
            led = BJLEDInstance(address=mac)
        else:
            led = BJLEDInstance()
        
        await led.initialize()
        click.echo("✅ Device connected, starting stress test...")
        
        # Stress test commands
        colors = [
            (255, 0, 0),    # Red
            (0, 255, 0),    # Green
            (0, 0, 255),    # Blue
            (255, 255, 0),  # Yellow
            (255, 0, 255),  # Magenta
        ]
        
        start_time = asyncio.get_event_loop().time()
        successful_commands = 0
        failed_commands = 0
        
        for i in range(commands):
            try:
                color = colors[i % len(colors)]
                
                with debugger.command_timer(f"stress_command_{i}", None):
                    await led.set_color_to_rgb(*color)
                
                successful_commands += 1
                
                if i % 10 == 0:  # Progress every 10 commands
                    click.echo(f"  Progress: {i}/{commands} commands")
                
                await asyncio.sleep(0.1)  # Brief pause
                
            except Exception as e:
                failed_commands += 1
                click.echo(f"  ❌ Command {i} failed: {e}")
        
        end_time = asyncio.get_event_loop().time()
        total_time = end_time - start_time
        
        # Turn off LED
        await led.turn_off()
        await led.disconnect()
        
        # Results
        click.echo(f"\n📊 STRESS TEST RESULTS")
        click.echo("=" * 50)
        click.echo(f"Total Commands: {commands}")
        click.echo(f"Successful: {successful_commands}")
        click.echo(f"Failed: {failed_commands}")
        click.echo(f"Success Rate: {(successful_commands/commands)*100:.1f}%")
        click.echo(f"Total Time: {total_time:.2f}s")
        click.echo(f"Commands/sec: {commands/total_time:.2f}")
        
        # Performance metrics
        metrics = debugger.performance_metrics
        click.echo(f"Avg Command Time: {metrics.get('avg_command_time', 0):.3f}s")
        click.echo(f"Max Command Time: {metrics.get('max_command_time', 0):.3f}s")
        click.echo(f"Min Command Time: {metrics.get('min_command_time', 0):.3f}s")
        
    except Exception as e:
        click.echo(f"❌ Stress test failed: {e}")
        debugger.log_error("stress_test", e)
    
    finally:
        if ctx.obj['export_report']:
            report_path = debugger.export_debug_report()
            click.echo(f"\n📄 Debug report saved: {report_path}")


@debug_cli.command()
@click.option('--days', '-d', default=7, help='Show logs from last N days')
@click.pass_context
def show_logs(ctx, days):
    """Show recent debug logs and reports."""
    debugger = ctx.obj['debugger']
    
    click.echo(f"📋 Debug logs from last {days} days:\n")
    
    try:
        debug_dir = debugger.debug_dir
        
        # Find log files
        log_files = list(debug_dir.glob("bluelights_debug_*.log"))
        report_files = list(debug_dir.glob("debug_report_*.json"))
        
        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        report_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Show recent logs
        click.echo("📄 LOG FILES:")
        for log_file in log_files[:5]:  # Show last 5 log files
            mtime = log_file.stat().st_mtime
            size = log_file.stat().st_size
            click.echo(f"  {log_file.name} ({size} bytes, {time.ctime(mtime)})")
        
        # Show recent reports
        click.echo(f"\n📊 DEBUG REPORTS:")
        for report_file in report_files[:5]:  # Show last 5 reports
            mtime = report_file.stat().st_mtime
            size = report_file.stat().st_size
            click.echo(f"  {report_file.name} ({size} bytes, {time.ctime(mtime)})")
        
        # Show summary of latest report
        if report_files:
            latest_report = report_files[0]
            click.echo(f"\n📈 LATEST REPORT SUMMARY ({latest_report.name}):")
            
            try:
                with open(latest_report, 'r') as f:
                    report_data = json.load(f)
                
                perf = report_data.get('performance_metrics', {})
                errors = report_data.get('errors', [])
                
                click.echo(f"  Session Duration: {perf.get('session_duration', 0):.1f}s")
                click.echo(f"  Commands Sent: {perf.get('commands_sent', 0)}")
                click.echo(f"  Command Failures: {perf.get('command_failures', 0)}")
                click.echo(f"  Connection Attempts: {perf.get('connection_attempts', 0)}")
                click.echo(f"  Errors Logged: {len(errors)}")
                
            except Exception as e:
                click.echo(f"  ❌ Could not read report: {e}")
        
        click.echo(f"\n📁 Debug directory: {debug_dir}")
        
    except Exception as e:
        click.echo(f"❌ Failed to show logs: {e}")


@debug_cli.command()
@click.pass_context
def summary(ctx):
    """Show current debug session summary."""
    debugger = ctx.obj['debugger']
    debugger.print_summary()


def main():
    """Main entry point for debug CLI."""
    import functools
    
    def async_command(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            return asyncio.run(f(*args, **kwargs))
        return wrapper
    
    # Apply async wrapper to async commands
    for cmd_name in ['system_check', 'scan_devices', 'test_device', 'stress_test']:
        if cmd_name in debug_cli.commands:
            debug_cli.commands[cmd_name].callback = async_command(debug_cli.commands[cmd_name].callback)
    
    debug_cli()


if __name__ == '__main__':
    main()
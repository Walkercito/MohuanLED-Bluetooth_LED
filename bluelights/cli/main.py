#!/usr/bin/env python3
"""
Command Line Interface for LED Controller.
"""
import asyncio
import click
import logging
import sys
from typing import Tuple, Optional
from pathlib import Path

try:
    from ..manager import BJLEDInstance
    from ..scanner import Scanner
    from ..config import get_config_manager
    from ..exceptions import BlueLightsException
except ImportError:
    # Fallback for development
    sys.path.append(str(Path(__file__).parent.parent))
    from manager import BJLEDInstance
    from scanner import Scanner
    from config import get_config_manager
    from exceptions import BlueLightsException

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.option('--config-dir', type=click.Path(), help='Configuration directory')
@click.pass_context
def cli(ctx, debug, config_dir):
    """LED Controller Command Line Interface."""
    ctx.ensure_object(dict)
    
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        ctx.obj['debug'] = True
    
    if config_dir:
        ctx.obj['config_dir'] = Path(config_dir)
    
    # Initialize config manager
    config_manager = get_config_manager()
    ctx.obj['config'] = config_manager.get()

@cli.command()
@click.pass_context
async def scan(ctx):
    """Scan for available LED devices."""
    try:
        click.echo("Scanning for LED devices...")
        scanner = Scanner()
        mac_address, device = await scanner.scan_led()
        
        if mac_address:
            click.echo(f"✓ Found LED device:")
            click.echo(f"  Name: {device.name}")
            click.echo(f"  MAC Address: {mac_address}")
            click.echo(f"  Metadata: {device.metadata}")
            
            # Scan for UUIDs
            click.echo("\nScanning for UUIDs...")
            uuids = await scanner.scan_uuids(mac_address)
            if uuids:
                click.echo("  Available UUIDs:")
                for uuid in uuids:
                    click.echo(f"    - {uuid}")
            else:
                click.echo("  No UUIDs found")
        else:
            click.echo("✗ No LED devices found")
            click.echo("Make sure your LED device is powered on and in pairing mode")
    
    except Exception as e:
        click.echo(f"✗ Error during scan: {e}", err=True)
        if ctx.obj.get('debug'):
            raise

@cli.command()
@click.option('--mac', help='MAC address of the LED device')
@click.option('--uuid', help='UUID for the LED device')
@click.option('--auto-discover', is_flag=True, help='Automatically discover device')
@click.pass_context
async def connect(ctx, mac, uuid, auto_discover):
    """Test connection to LED device."""
    config = ctx.obj['config']
    
    try:
        if auto_discover:
            click.echo("Auto-discovering LED device...")
            led = BJLEDInstance()
            await led.initialize()
        else:
            # Use provided or config values
            mac_addr = mac or config.led.mac_address
            uuid_addr = uuid or config.led.uuid
            
            if not mac_addr or not uuid_addr:
                click.echo("✗ MAC address and UUID are required", err=True)
                click.echo("Use --mac and --uuid, or configure them in settings")
                return
            
            click.echo(f"Connecting to {mac_addr}...")
            led = BJLEDInstance(address=mac_addr, uuid=uuid_addr)
            await led._ensure_connected()
        
        click.echo("✓ Connected successfully!")
        
        # Test basic commands
        click.echo("Testing basic commands...")
        await led.turn_on()
        click.echo("  ✓ Turn ON")
        
        await asyncio.sleep(1)
        
        await led.set_color_to_rgb(255, 0, 0)
        click.echo("  ✓ Set color to red")
        
        await asyncio.sleep(2)
        
        await led.turn_off()
        click.echo("  ✓ Turn OFF")
        
        await led._disconnect()
        click.echo("✓ Test completed successfully!")
    
    except BlueLightsException as e:
        click.echo(f"✗ LED Error: {e}", err=True)
    except Exception as e:
        click.echo(f"✗ Unexpected error: {e}", err=True)
        if ctx.obj.get('debug'):
            raise

@cli.command()
@click.option('--red', '-r', type=click.IntRange(0, 255), default=255, help='Red value (0-255)')
@click.option('--green', '-g', type=click.IntRange(0, 255), default=255, help='Green value (0-255)')
@click.option('--blue', '-b', type=click.IntRange(0, 255), default=255, help='Blue value (0-255)')
@click.option('--duration', '-d', type=float, default=5.0, help='Duration in seconds')
@click.option('--mac', help='MAC address of the LED device')
@click.option('--uuid', help='UUID for the LED device')
@click.pass_context
async def set_color(ctx, red, green, blue, duration, mac, uuid):
    """Set LED color."""
    config = ctx.obj['config']
    
    try:
        # Initialize LED
        mac_addr = mac or config.led.mac_address
        uuid_addr = uuid or config.led.uuid
        
        if mac_addr and uuid_addr:
            led = BJLEDInstance(address=mac_addr, uuid=uuid_addr)
            await led._ensure_connected()
        else:
            led = BJLEDInstance()
            await led.initialize()
        
        click.echo(f"Setting color to RGB({red}, {green}, {blue}) for {duration}s...")
        
        await led.turn_on()
        await led.set_color_to_rgb(red, green, blue)
        
        if duration > 0:
            await asyncio.sleep(duration)
            await led.turn_off()
        
        await led._disconnect()
        click.echo("✓ Color set successfully!")
    
    except Exception as e:
        click.echo(f"✗ Error setting color: {e}", err=True)
        if ctx.obj.get('debug'):
            raise

@cli.command()
@click.option('--effect', type=click.Choice(['rainbow', 'breathing', 'strobe']), 
              required=True, help='Effect to apply')
@click.option('--duration', '-d', type=float, default=10.0, help='Effect duration')
@click.option('--color', '-c', default='255,255,255', help='Color for effect (R,G,B)')
@click.option('--mac', help='MAC address of the LED device')
@click.option('--uuid', help='UUID for the LED device')
@click.pass_context
async def effect(ctx, effect, duration, color, mac, uuid):
    """Apply effects to the LED."""
    config = ctx.obj['config']
    
    try:
        # Parse color
        try:
            r, g, b = map(int, color.split(','))
            if not all(0 <= c <= 255 for c in [r, g, b]):
                raise ValueError("RGB values must be between 0 and 255")
        except ValueError as e:
            click.echo(f"✗ Invalid color format: {e}", err=True)
            return
        
        # Initialize LED
        mac_addr = mac or config.led.mac_address
        uuid_addr = uuid or config.led.uuid
        
        if mac_addr and uuid_addr:
            led = BJLEDInstance(address=mac_addr, uuid=uuid_addr)
            await led._ensure_connected()
        else:
            led = BJLEDInstance()
            await led.initialize()
        
        await led.turn_on()
        
        click.echo(f"Applying {effect} effect for {duration}s...")
        
        if effect == 'rainbow':
            await led.rainbow_cycle(duration / 10)  # Adjust speed
        elif effect == 'breathing':
            await led.breathing_light((r, g, b), duration)
        elif effect == 'strobe':
            flashes = int(duration * 5)  # 5 flashes per second
            await led.strobe_light((r, g, b), duration, flashes)
        
        await led.turn_off()
        await led._disconnect()
        click.echo("✓ Effect completed!")
    
    except Exception as e:
        click.echo(f"✗ Error applying effect: {e}", err=True)
        if ctx.obj.get('debug'):
            raise

@cli.command()
@click.pass_context
def config_show(ctx):
    """Show current configuration."""
    config = ctx.obj['config']
    
    click.echo("Current Configuration:")
    click.echo(f"  LED MAC Address: {config.led.mac_address or 'Not set'}")
    click.echo(f"  LED UUID: {config.led.uuid or 'Not set'}")
    click.echo(f"  Auto Connect: {config.led.auto_connect}")
    click.echo(f"  Debug Mode: {config.debug}")
    click.echo(f"  Log Level: {config.log_level}")

@cli.command()
@click.option('--mac', help='Set MAC address')
@click.option('--uuid', help='Set UUID')
@click.option('--auto-connect/--no-auto-connect', help='Enable/disable auto connect')
@click.pass_context
def config_set(ctx, mac, uuid, auto_connect):
    """Update configuration."""
    config_manager = get_config_manager()
    
    updates = {}
    if mac:
        updates['mac_address'] = mac
        click.echo(f"MAC address set to: {mac}")
    
    if uuid:
        updates['uuid'] = uuid
        click.echo(f"UUID set to: {uuid}")
    
    if auto_connect is not None:
        updates['auto_connect'] = auto_connect
        click.echo(f"Auto connect set to: {auto_connect}")
    
    if updates:
        config_manager.update_led_config(**updates)
        click.echo("✓ Configuration updated!")
    else:
        click.echo("No configuration changes specified")

@cli.command()
def gui():
    """Launch the graphical interface."""
    try:
        from ..gui.app import cli_main
        click.echo("Launching GUI...")
        cli_main()
    except ImportError:
        click.echo("✗ GUI dependencies not available", err=True)
        click.echo("Install with: pip install bluelights[gui]")

def scan_devices():
    """Entry point for device scanning."""
    asyncio.run(Scanner().run())

def main():
    """Main CLI entry point."""
    # Make the CLI async-compatible
    import functools
    
    def async_command(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            return asyncio.run(f(*args, **kwargs))
        return wrapper
    
    # Apply async wrapper to async commands
    for cmd_name in ['scan', 'connect', 'set_color', 'effect']:
        if cmd_name in cli.commands:
            cli.commands[cmd_name].callback = async_command(cli.commands[cmd_name].callback)
    
    cli()

if __name__ == '__main__':
    main()
"""
Announce the server on the local network, so a frame can find it without
anyone typing its address.

The server registers an mDNS (DNS-SD) service of type _epf._tcp, the same
mechanism ESPHome devices use to be found by Home Assistant, only the other
way round: the frame sleeps between wake-ups and cannot wait to be found, so
the server announces itself and a frame looks it up. The record carries the
address and port of the settings page, which is also the base URL the frame
downloads from, and TXT entries for the path and the protocol version.

mDNS is multicast and never leaves the local network segment. From inside a
container on Docker's default bridge network it does not reach the LAN at
all, so the container has to use the host's network (network_mode: host,
Linux only); see docker-compose.yml. A frame that cannot find the server
falls back to the address entered in its captive portal, as before.

Environment:
  EPF_DISCOVERY            'off' disables the announcement
  EPF_ADVERTISE_ADDRESS    the address to announce, when the one the default
                           route leaves from is not the right one
"""
import atexit
import ipaddress
import os
import socket
import threading

SERVICE_TYPE = '_epf._tcp.local.'
# Bumped when what a frame may expect from the server changes incompatibly
API_VERSION = '1'

_zeroconf = None


def _log(message):
    """ Start-up diagnostics, flushed: a container's stdout is not a terminal and would hold them back """
    print(f"Discovery: {message}", flush=True)


def lan_address():
    """ The IPv4 address the default route leaves from, or None without one """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            # Connecting a UDP socket only picks a route; nothing is sent
            probe.connect(('10.254.254.254', 1))
            return probe.getsockname()[0]
    except OSError:
        return None


def _looks_like_docker_bridge(address):
    """ Inside a container on a Docker bridge network, where multicast stays put """
    return os.path.exists('/.dockerenv') and ipaddress.ip_address(address) in ipaddress.ip_network('172.16.0.0/12')


def start(port):
    """
    Announce the server on a background thread; registering takes a couple of
    seconds of probing. Never raises: without discovery the frame still works
    with an address entered by hand.
    """
    if os.getenv('EPF_DISCOVERY', 'on').lower() in ('off', '0', 'false', 'no'):
        _log("off (EPF_DISCOVERY)")
        return
    threading.Thread(target=_register, args=(port,), daemon=True).start()


def _register(port):
    global _zeroconf
    address = os.getenv('EPF_ADVERTISE_ADDRESS') or lan_address()
    if not address:
        _log("no network address found, not announcing")
        return
    try:
        from zeroconf import IPVersion, ServiceInfo, Zeroconf

        host = socket.gethostname().split('.')[0] or 'epf'
        info = ServiceInfo(
            SERVICE_TYPE,
            f'EPF server on {host}.{SERVICE_TYPE}',
            port=port,
            properties={'path': '/', 'api': API_VERSION},
            # Named after the address, so two servers on machines with the same
            # host name do not claim the same host record with different addresses
            server=f"epf-{address.replace('.', '-')}.local.",
            addresses=[socket.inet_aton(address)],
        )
        zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
        # Another server under the same name gets a numbered one instead
        zeroconf.register_service(info, allow_name_change=True)
        _zeroconf = zeroconf
        atexit.register(_unregister, info)
        _log(f"announcing http://{address}:{port}/ as '{info.name}'")
        if _looks_like_docker_bridge(address):
            _log("this looks like a Docker bridge network, which keeps the announcement inside "
                 "the container; use network_mode: host for frames to find the server")
    except Exception as error:
        _log(f"could not announce the server: {error}")


def _unregister(info):
    """ Tell listeners the server is gone, so they do not wait for the record to expire """
    try:
        _zeroconf.unregister_service(info)
        _zeroconf.close()
    except Exception:
        pass

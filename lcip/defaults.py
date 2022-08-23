"""lcip - configuration defaults"""

from pathlib import Path
from shutil import which
import grp
import pwd


def _get_tool_paths(*tools):
    """Returns a mapping of tool name and its full path as a dict
    """
    tool_paths = {}
    for tool in tools:
        tool_path = which(tool)
        if tool_path is not None:
            tool_paths[tool] = tool_path
    if missing_tools := set(tools) - set(tool_paths):
        raise RuntimeError(f'{", ".join(missing_tools)} command(s) not found in system path')
    else:
        return tool_paths


LIBVIRT_POOL = 'default'
LIBVIRT_POOL_DIR = Path('/var/lib/libvirt/images')
LIBVIRT_VOL_OWNER = pwd.getpwnam('libvirt-qemu')[2]
LIBVIRT_VOL_GROUP = grp.getgrnam('kvm')[2]
LCIP_CONFIG_DIR = Path('/etc/lcip')
LCIP_WORK_DIR = Path('/var/lib/lcip')
MAX_CPU = 16
MAX_DISK = 4000
MAX_MEMORY = 32768
MAX_VLAN = 4095
MEMORY_STEPS = 64
MIN_DISK = 10
MIN_MEMORY = 512
MIN_VLAN = 1
TOOLS=_get_tool_paths('qemu-img', 'cloud-localds')

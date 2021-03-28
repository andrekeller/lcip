"""lcip - configuration defaults"""

from pathlib import Path
import grp
import pwd

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
TOOLS = {
    'qemu-img': '/usr/bin/qemu-img',
    'cloud-localds': '/usr/bin/cloud-localds',
}

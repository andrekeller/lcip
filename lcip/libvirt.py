"""lcip - libvirt api"""

# stdlib
from contextlib import suppress
from functools import partial
from pathlib import Path
from xml.dom import minidom
import xml.etree.ElementTree as ElementTree

# 3rd-party
import libvirt

# lcip
from lcip.defaults import LIBVIRT_POOL_DIR


class Libvirt:
    """Libvirt interface"""

    def __init__(self, pool, libvirt_url=None):
        """initialize connection to libvirt"""
        self._connection = libvirt.open(libvirt_url) # pylint: disable=maybe-no-member
        self._pool = self._connection.storagePoolLookupByName(pool)
        if self._pool is None:
            raise RuntimeError(f'libvirt storage pool {pool} not found')

    def pool_refresh(self):
        """refresh storage pool"""
        self._pool.refresh()

    def define(self, xml):
        """define libvirt resource from xml"""
        self._connection.defineXML(xml)

    def start(self, name):
        """enable autostart and start domain"""
        domain = self._connection.lookupByName(name)
        domain.setAutostart(True)
        domain.create()

    def __del__(self):
        """ensure connection to libvirt is closed"""
        if self._connection:
            with suppress(libvirt.libvirtError): # pylint: disable=maybe-no-member
                self._connection.close()


class LibvirtDomain:
    """Libvirt domain definition"""

    def __init__(self, vmdefinition):
        """intialize new domain definition"""
        self.vmdefinition = vmdefinition

    # pylint: disable=too-many-arguments
    def _add_element(self, parent, name, attributes=None, text=None, children=None):
        """simplified interface for adding xml elements"""
        element = ElementTree.Element(name)
        if attributes:
            for attribute, value in attributes.items():
                element.attrib[attribute] = value
        if text:
            element.text = text
        if children:
            for child, params in children.items():
                self._add_element(element,
                                  child,
                                  text=params.get('text', None),
                                  attributes=params.get('attributes', None),
                                  children=params.get('children', None))
        parent.append(element)

    def _interface(self, bridge, vlan=None):
        """create libvirt interface definition"""
        interface = ElementTree.Element('interface')
        interface.attrib['type'] = 'bridge'

        add_to_interface = partial(self._add_element, interface)

        add_to_interface('source', attributes={'bridge': bridge})
        add_to_interface('model', attributes={'type': 'virtio'})
        add_to_interface('virtualport', attributes={'type': 'openvswitch'})
        if vlan:
            add_to_interface('vlan', children={'tag': {'attributes': {'id': str(vlan)}}})
        return interface

    def _disk(self, source, dev, driver='raw', readonly=False):
        """create libvirt disk definition"""
        disk = ElementTree.Element('disk')
        disk.attrib['type'] = 'file'
        disk.attrib['device'] = 'disk'

        add_to_disk = partial(self._add_element, disk)

        add_to_disk('driver', attributes={'name': 'qemu', 'type': driver})
        add_to_disk('source', attributes={'file': source})
        add_to_disk('target', attributes={'dev': dev, 'bus': 'virtio'})

        if readonly:
            add_to_disk('readonly')

        return disk

    @property
    def image(self):
        """path to domains root disk"""
        return Path(LIBVIRT_POOL_DIR, f'{self.vmdefinition["fqdn"]}-root.img')

    @property
    def seed(self):
        """path to domains seed image"""
        return Path(LIBVIRT_POOL_DIR, f'{self.vmdefinition["fqdn"]}-seed.iso')

    @property
    def xml(self):
        """xml representation of libvirt domain"""
        xml = ElementTree.Element('domain')
        xml.attrib['type'] = 'kvm'
        add_to_domain = partial(self._add_element, xml)

        add_to_domain('name', text=self.vmdefinition['fqdn'])
        add_to_domain('on_crash', text='destroy')
        add_to_domain('on_poweroff', text='destroy')
        add_to_domain('on_reboot', text='restart')

        add_to_domain('vcpu', text=str(self.vmdefinition['cpu']))
        add_to_domain('memory', attributes={'unit': 'MiB'}, text=str(self.vmdefinition['memory']))
        add_to_domain('memoryBacking', children={'hugepages': {}})

        add_to_domain('os', children={
            'boot': {'attributes': {'dev': 'hd'}},
            'type': {'text': 'hvm', 'attributes': {'arch': 'x86_64', 'machine': 'pc'}},
        })

        add_to_domain('features', children={
            'acpi': {},
            'apic': {},
        })

        add_to_domain('clock', attributes={'offset': 'utc'})

        devices = ElementTree.Element('devices')
        add_to_devices = partial(self._add_element, devices)
        add_to_devices('emulator', text='/usr/bin/qemu-system-x86_64')
        add_to_devices('console', attributes={'type': 'pty'})
        add_to_devices('input', attributes={'type': 'keyboard', 'bus': 'ps2'})
        add_to_devices(
            'graphics',
            attributes={'type': 'spice', 'port': '-1', 'tlsPort': '-1', 'autoport': 'yes'},
            children={'image': {'attributes': {'compression': 'off'}}},
        )
        add_to_devices(
            'video',
            children={'model': {'attributes': {'type': 'virtio'}}},
        )
        devices.append(self._interface(
            self.vmdefinition['network']['ovs_bridge'],
            self.vmdefinition['network'].get('ovs_vlan', None),
        ))
        devices.append(self._disk(
            source=str(self.image),
            dev='vda',
        ))
        devices.append(self._disk(
            source=str(self.seed),
            dev='vdb',
            driver='raw',
            readonly=True,
        ))
        add_to_devices('memballoon', attributes={'model': 'virtio'})

        xml.append(devices)

        return minidom.parseString(
            ElementTree.tostring(xml, encoding='utf8')
        ).toprettyxml(indent='  ')

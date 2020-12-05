"""lcip - vm definition api"""

# stdlib
import ipaddress
from pathlib import Path
import re
import yaml

# 3rd-party
from jinja2 import Template
from jinja2.exceptions import TemplateSyntaxError

# lcip
from lcip.defaults import LCIP_CONFIG_DIR, LCIP_WORK_DIR
from lcip.defaults import MAX_CPU, MAX_DISK, MAX_MEMORY, MAX_VLAN, \
    MEMORY_STEPS, MIN_DISK, MIN_MEMORY, MIN_VLAN


class DefinitionValidator:
    """Validator for vmdefinitions"""

    mandatory = {'cpu', 'memory', 'disk', 'template', 'ssh_keys', 'network'}
    optional = {'rng'}
    supported = mandatory | optional

    def validate(self, vmname):
        """validate vmdefinition and return dict with validated options"""
        fqdn_re = re.compile(r'^(?P<fqdn>(?P<host>[^.]+)\.[a-z0-9-]+(?:[a-z0-9-.]+)[^.])$')
        fqdn_match = fqdn_re.match(vmname)
        if fqdn_match:
            validated = {
                'fqdn': fqdn_match.groupdict()['fqdn'],
                'host': fqdn_match.groupdict()['host'],
            }
        else:
            raise ValueError(f'{vmname} is not a valid fully qualified domain name')

        with open(Path(LCIP_CONFIG_DIR, 'definitions', f'{vmname}.yaml'), 'r') as vmdefinition:
            vmdef = yaml.load(vmdefinition, Loader=yaml.SafeLoader)
        unsupported = set(vmdef.keys()) - self.supported
        if unsupported:
            raise ValueError(f'invalid option(s) in vmdefinition: {unsupported}')
        missing = self.mandatory - set(vmdef.keys())
        if missing:
            raise ValueError(f'missing option(s) in vmdefinition: {missing}')

        for option, value in vmdef.items():
            # call validation method for each option
            validated.update(getattr(self, option)(value))
        return validated

    @staticmethod
    def cpu(cpu):
        """Validate cpu definition"""
        if (not isinstance(cpu, bool)
                and isinstance(cpu, int)
                and 1 <= cpu <= MAX_CPU):
            return {'cpu': cpu}
        raise ValueError(f'{cpu} is not a valid amount of CPUs')

    @staticmethod
    def memory(memory):
        """Validate memory definition"""
        if (not isinstance(memory, bool)
                and isinstance(memory, int)
                and MIN_MEMORY <= memory <= MAX_MEMORY
                and memory % MEMORY_STEPS == 0):
            return {'memory': memory}
        raise ValueError(f'{memory} is not a valid amount of memory')

    @staticmethod
    def disk(disk):
        """Validate disk definition"""
        if (not isinstance(disk, bool)
                and isinstance(disk, int)
                and MIN_DISK <= disk <= MAX_DISK):
            return {'disk': disk}
        raise ValueError(f'{disk} is not a valid amount of disk space')

    @staticmethod
    def template(template):
        """Validate template definition"""
        validated = {}
        try:
            template_dir = Path(LCIP_CONFIG_DIR, 'templates', template)
            if not template_dir.is_dir():
                raise ValueError(f'{template_dir} template directory does not exist')
        except (TypeError, ValueError) as error:
            raise ValueError(f'{template} is not a valid template: {error}')

        try:
            with open(Path(template_dir, 'cloud-init-networkconfig.yaml')) as networkconfig:
                validated['networkconfig_template'] = Template(
                    networkconfig.read(), trim_blocks=True
                )
        except TemplateSyntaxError as error:
            raise ValueError(f'networkconfig template {template} has syntax errors: {error}')
        except (TypeError, OSError) as error:
            raise ValueError(f'{template} has no valid networkconfig template: {error}')

        try:
            with open(Path(template_dir, 'cloud-init-userdata.yaml')) as userdata:
                validated['userdata_template'] = Template(
                    userdata.read(), trim_blocks=True
                )
        except TemplateSyntaxError as error:
            raise ValueError(f'user-data template {template} has syntax errors: {error}')
        except (TypeError, OSError) as error:
            raise ValueError(f'{template} has no valid user-data template: {error}')

        image = Path(LCIP_WORK_DIR, 'images', f'{template}.img')
        if image.is_file():
            validated['image'] = image
        else:
            raise ValueError(f'No image found for template {template}: {image} is not a file')

        return validated

    @staticmethod
    def ssh_keys(ssh_keys):
        """Validate ssh_keys definition"""
        ssh_key_re = re.compile(
            r'^(?:ecdsa-sha2-nistp256|ecdsa-sha2-nistp384|ecdsa-sha2-nistp521|ssh-ed25519|ssh-rsa)'
            r'\s+[^\s]+\s+[^\s]+$'
        )
        if (isinstance(ssh_keys, list) and
                any(ssh_key_re.match(ssh_key) for ssh_key in ssh_keys)):
            return {'ssh_keys': ssh_keys}
        raise ValueError(f'{ssh_keys} is not a valid list of ssh authorized keys')

    @staticmethod
    def rng(rng):
        """Validate rng definition"""
        if isinstance(rng, bool):
            if rng:
                return {'rng': True}
            return {}
        raise ValueError(f'{rng} is not a valid configuration for option rng)')

    @staticmethod
    def network(network):
        """Validate network definition"""
        validated = {}
        if not isinstance(network, dict):
            raise ValueError(f'{network} is not a valid dict')

        mandatory = {'address4', 'gateway4', 'nameservers', 'ovs_bridge'}
        optional = {'address6', 'gateway6', 'ovs_vlan'}
        supported = mandatory | optional


        unsupported = set(network.keys()) - supported
        if unsupported:
            raise ValueError(f'invalid option(s) for network: {unsupported}')
        missing = mandatory - set(network.keys())
        if missing:
            raise ValueError(f'missing option(s) for network: {missing}')

        if not isinstance(network['ovs_bridge'], str):
            raise ValueError(f'{network["ovs_bridge"]} is not a valid ovs_bridge')
        validated['ovs_bridge'] = network['ovs_bridge']

        if 'ovs_vlan' in network:
            if (not isinstance(network['ovs_vlan'], bool)
                    and isinstance(network['ovs_vlan'], int)
                    and MIN_VLAN <= network['ovs_vlan'] <= MAX_VLAN):
                validated['ovs_vlan'] = network['ovs_vlan']
            else:
                raise ValueError(f'{network["ovs_vlan"]} is not a valid ovs_vlan')

        validated['address4'] = ipaddress.IPv4Interface(network['address4'])

        if 'address6' in network:
            validated['address6'] = ipaddress.IPv6Interface(network['address6'])

        validated['gateway4'] = ipaddress.IPv4Address(network['gateway4'])

        if 'gateway6' in network:
            validated['gateway6'] = ipaddress.IPv6Address(network['gateway6'])

        if not isinstance(network['nameservers'], list):
            raise ValueError(f'{network["nameservers"]} is not a valid list of nameservers')
        validated['nameservers'] = [
            ipaddress.IPv4Address(nameserver) for nameserver in network['nameservers']
        ]

        return {'network': validated}

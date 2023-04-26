#!/usr/bin/env python3
"""LibVirt/cloud-init provisioner"""

# stdlib
from argparse import ArgumentParser
from shutil import copyfile
from subprocess import run
import os

# lcip
from lcip.cloudinit import CloudInit
from lcip.defaults import TOOLS, LIBVIRT_POOL, LIBVIRT_VOL_OWNER, LIBVIRT_VOL_GROUP
from lcip.definition import DefinitionValidator
from lcip.libvirt import Libvirt, LibvirtDomain


def provision():
    """generate cloud-init configuration and provision a new VM"""

    parser = ArgumentParser()
    parser.add_argument("name")
    parser.add_argument(
        "--no-provision", action="store_false", dest="provision", default=True
    )
    parser.add_argument("--no-start", action="store_false", dest="start", default=True)
    cli_args = parser.parse_args()

    vmdefinition = DefinitionValidator().validate(cli_args.name)
    seed_iso = CloudInit(vmdefinition).generate_seed_iso()

    if cli_args.provision:
        libvirt = Libvirt(pool=LIBVIRT_POOL)
        domain = LibvirtDomain(vmdefinition)
        if domain.seed.is_file():
            raise RuntimeError(f"Volume {domain.seed} already exists")
        copyfile(seed_iso, domain.seed)
        os.chown(domain.seed, LIBVIRT_VOL_OWNER, LIBVIRT_VOL_GROUP)
        os.chmod(domain.seed, 0o770)

        if domain.image.is_file():
            raise RuntimeError(f"Volume {domain.image} already exists")
        run(
            [
                TOOLS["qemu-img"],
                "convert",
                "-f",
                "qcow2",
                "-O",
                "raw",
                "-o",
                "preallocation=falloc",
                vmdefinition["image"],
                domain.image,
            ],
            check=True,
            capture_output=True,
        )
        run(
            [
                TOOLS["qemu-img"],
                "resize",
                "-f",
                "raw",
                "--preallocation=falloc",
                str(domain.image),
                f'{vmdefinition["disk"]}G',
            ],
            check=True,
            capture_output=True,
        )
        os.chown(domain.image, LIBVIRT_VOL_OWNER, LIBVIRT_VOL_GROUP)
        os.chmod(domain.image, 0o770)
        libvirt.pool_refresh()

        libvirt.define(domain.xml)
        if cli_args.start:
            libvirt.start(cli_args.name)

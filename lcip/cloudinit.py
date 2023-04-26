"""lcip - cloud-init api"""

# stdlib
import os
from pathlib import Path
from subprocess import run

# lcip
from lcip.defaults import LCIP_WORK_DIR, TOOLS


class CloudInit:
    """cloud-init configuration and seed image generator"""

    def __init__(self, vmdefinition):
        self.vmdefinition = vmdefinition

    def generate_seed_iso(self):
        """Generate vm specific seed image"""
        seed_dir = Path(LCIP_WORK_DIR, f'{self.vmdefinition["fqdn"]}-seed')
        os.makedirs(seed_dir, exist_ok=True)

        userdata_yaml = Path(seed_dir, "userdata.yaml")
        networkconfig_yaml = Path(seed_dir, "networkconfig.yaml")
        seed_iso = Path(seed_dir, "seed.iso")

        with open(userdata_yaml, "w", encoding="utf-8") as userdata:
            userdata.write(self.userdata)
        with open(networkconfig_yaml, "w", encoding="utf-8") as networkconfig:
            networkconfig.write(self.networkconfig)

        run(
            [
                TOOLS["cloud-localds"],
                "-v",
                f"--network-config={str(networkconfig_yaml)}",
                str(seed_iso),
                str(userdata_yaml),
            ],
            check=True,
            capture_output=True,
        )

        return seed_iso

    @property
    def networkconfig(self):
        """rendered networkconfig"""
        return self.vmdefinition["networkconfig_template"].render(
            self.vmdefinition["network"]
        )

    @property
    def userdata(self):
        """rendered userdata"""
        return self.vmdefinition["userdata_template"].render(
            fqdn=self.vmdefinition["fqdn"],
            host=self.vmdefinition["host"],
            ssh_keys=self.vmdefinition["ssh_keys"],
        )

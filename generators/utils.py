"""Helpers."""

import os
import yaml

HERE = os.path.abspath(os.path.dirname(__file__))


def map_fabric(size, vendor):
    """Generate initial fabric data."""
    with open(
        f"{HERE}/fabrics/{vendor}_{size}.yaml",
        "r",
        encoding="UTF8",
    ) as file:
        try:
            return yaml.safe_load(file)
        except yaml.YAMLError as exc:
            print(exc)
            return None


def generate_interfaces(device_type, role):
    """Generate interfaces."""
    with open(
        f"{HERE}/interfaces/{device_type.lower()}.yaml",
        "r",
        encoding="UTF8",
    ) as file:
        try:
            device = yaml.safe_load(file)
        except yaml.YAMLError as exc:
            print(exc)
    # device = DEVICES[device_type.lower()]
    interfaces = []
    for item in device.get("interfaces", []):
        if item.get("from", "") and item.get("to", ""):
            for i in range(int(item.get("from")), int(item.get("to")) + 1):
                if role == "spine":
                    int_role = item.get("role")[1]
                elif role == "leaf":
                    int_role = item.get("role")[0]
                else:
                    int_role = item.get("role")
                interfaces.append(
                    {
                        "name": item.get("name") + str(i),
                        "speed": item.get("speed"),
                        "role": int_role,
                    }
                )

        else:
            interfaces.append(
                {
                    "name": item.get("name"),
                    "speed": item.get("speed", ""),
                    "role": item.get("role"),
                }
            )
    return interfaces


DEVICES = {
    "ccs-720dp-48s-2f": {
        "interfaces": [
            {
                "name": "FastEthernet0/",
                "from": "0",
                "to": "47",
                "speed": 1000,
                "role": ["server", "leaf"],
            },
            {
                "name": "GigabitEthernet0/",
                "from": "0",
                "to": "7",
                "speed": 10000,
                "role": ["spine", "uplink"],
            },
            {"name": "mgmt", "speed": 1000, "role": "management"},
            {"name": "loopback0", "role": "loopback"},
            {"name": "loopback1", "role": "vtep"},
        ]
    },
    "dcs-7280dr3-24-f": {
        "interfaces": [
            {
                "name": "FastEthernet0/",
                "from": "0",
                "to": "23",
                "speed": 1000,
                "role": ["server", "uplink"],
            },
            {
                "name": "GigabitEthernet0/",
                "from": "0",
                "to": "7",
                "speed": 10000,
                "role": ["spine", "uplink"],
            },
            {"name": "mgmt", "speed": 1000, "role": "management"},
            {"name": "loopback0", "role": "loopback"},
            {"name": "loopback1", "role": "vtep"},
        ]
    },
}

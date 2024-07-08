"""Infrastructure generator"""

import os
from typing import Dict, List
from ipaddress import IPv4Network
import yaml
from infrahub_sdk import InfrahubNode
from infrahub_sdk.generator import InfrahubGenerator
from infrahub_sdk.batch import InfrahubBatch
from infrahub_sdk.exceptions import GraphQLError

# from utils import map_fabric  # , generate_interfaces

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


class TopologyGenerator(InfrahubGenerator):
    """Generate topology."""

    # def __init__(self, **kwargs):
    #     super().__init__(**kwargs)
    #     self.pools = None

    def populate_local_store(self, objects: List[InfrahubNode], key_type: str):
        """Populate local store."""

        for obj in objects:
            key = getattr(obj, key_type)
            if key:
                self.store.set(key=key.value, node=obj)

    async def create_and_save(
        self, object_name: str, kind_name: str, data: Dict, **kwargs
    ) -> InfrahubNode:
        """Creates an object, saves it and handles failures."""
        allow_upsert = kwargs.get("allow_upsert", True)
        retrieved_on_failure = kwargs.get("retrieved_on_failure", True)
        try:
            obj = await self.client.create(
                branch=self.branch, kind=kind_name, data=data
            )
            await obj.save(allow_upsert=allow_upsert)
            print(f"Created/Updated {kind_name} {object_name}")
            self.store.set(key=object_name, node=obj)
        except GraphQLError as exc:
            if retrieved_on_failure:
                obj = await self.client.get(kind=kind_name, name__value=object_name)
                self.store.set(key=object_name, node=obj)
            print(exc)
        return obj

    async def create_and_add_to_batch(
        self,
        object_name: str,
        kind_name: str,
        data: Dict,
        batch: InfrahubBatch,
        **kwargs,
    ) -> InfrahubNode:
        """Creates an object and adds it to a batch for deferred saving."""
        allow_upsert = kwargs.get("allow_upsert", True)
        try:
            obj = await self.client.create(
                branch=self.branch, kind=kind_name, data=data
            )
            batch.add(task=obj.save, allow_upsert=allow_upsert, node=obj)
            print(f"Addred {kind_name} {object_name} to the batch.")
            self.store.set(key=object_name, node=obj)
        except GraphQLError as exc:
            print(exc)
        return obj

    async def create_sites(self, topology_name, city_name, description):
        """Generate sites."""
        if not self.store.get(key=topology_name, raise_when_missing=False):
            data = {
                "name": topology_name,
                "shortname": topology_name,
                "parent": await self.client.get(
                    kind="LocationCity", name__value=city_name
                ),
                "description": description,
            }
            await self.create_and_save(
                object_name=topology_name,
                kind_name="LocationSite",
                data=data,
            )

    async def create_subnets(self, site, prefixes):
        """Generate subnets."""
        for network_type, subnet in prefixes.items():
            if not self.store.get(key=IPv4Network(subnet), raise_when_missing=False):
                data = {
                    "prefix": subnet,
                    "description": f"{site} prefix for {network_type}",
                    "location": self.store.get(key=site),
                    "status": "active",
                    "role": network_type,
                    "organization": self.store.get(key="Technology Partner"),
                    "is_pool": True,
                }
                await self.create_and_save(
                    object_name=subnet,
                    kind_name="InfraPrefix",
                    data=data,
                )
            if network_type == "technical":
                pools = list(IPv4Network(subnet).subnets(new_prefix=23))
                ip_pools = list(IPv4Network(pools[0]).subnets(new_prefix=24))
                for key, prefix in enumerate([pools[1], ip_pools[0], ip_pools[1]]):
                    if not self.store.get(
                        key=IPv4Network(prefix), raise_when_missing=False
                    ):
                        if key == 0:
                            role = "technical"
                        elif key == 1:
                            role = "inband"
                        else:
                            role = "vtep"
                        data = {
                            "prefix": prefix,
                            "description": f"{site} {network_type} prefix for {role} connections",
                            "location": self.store.get(key=site),
                            "status": "active",
                            "role": role,
                            "is_pool": True,
                            "organization": self.store.get(key="Technology Partner"),
                        }
                        await self.create_and_save(
                            object_name=prefix,
                            kind_name="InfraPrefix",
                            data=data,
                        )

    async def create_asns(self, site, asn):
        """Generate ASNs."""
        if not self.store.get(key=f"AS{asn}", raise_when_missing=False):
            data = {
                "name": f"AS{asn}",
                "asn": asn,
                "description": f"{site} ASN",
                "location": self.store.get(key=site),
                "status": "active",
                "organization": self.store.get(key="Technology Partner"),
            }
            await self.create_and_save(
                object_name=f"AS{asn}",
                kind_name="InfraAutonomousSystem",
                data=data,
            )

    async def create_topology_elements(self, size, vendor, topology, topology_id):
        """Generate topology elements."""
        # print(size, vendor)
        if size != "custom" and vendor:
            batch = await self.client.create_batch()
            for device in map_fabric(size, vendor):
                name = f"{topology}-{device.get('role')}s"
                data = {
                    "name": {"value": name, "is_protected": True},
                    "description": f"{topology} {device.get('role')}s",
                    "quantity": device.get("quantity"),
                    "device_role": {"value": device.get("role")},
                    "device_type": self.store.get(
                        key=device.get("model"), raise_when_missing=False
                    ),
                    "topology": topology_id,
                    "mtu": 9000,
                }
                if device.get("role") == "leaf":
                    data["mlag_support"] = True
                await self.create_and_add_to_batch(
                    object_name=f"{topology}-{device.get('role')}s",
                    kind_name="TopologyPhysicalElement",
                    data=data,
                    batch=batch,
                )
            async for _, result in batch.execute():
                if result:
                    print(f"problem {result}")

    async def create_pools(self, location):
        """Get pools for subnets."""

        pools = {
            role: []
            for role in [
                "management",
                "inband",
                "vtep",
                "p2p",
                "public",
            ]
        }
        for prefix in await self.client.filters(
            "InfraPrefix",
            location__name__value=location,
            role__values=["management", "vtep", "p2p", "public", "inband"],
            branch=self.branch,
        ):
            role = prefix.role.value
            if role in pools:
                pools[role].append(prefix.prefix.value.hosts())

    async def create_ip(self, data, name):
        """Create IP Address."""
        await self.create_and_save(
            object_name=name,
            kind_name="InfraIPAddress",
            data=data,
        )

    # async def create_interfaces(self, device):
    #     """Create interfaces."""
    #     kind = "InfraInterfaceL3"
    # configured_interfaces = self.store.get(key=device.name.value).interfaces.peers
    # for interface in generate_interfaces(device.device_type.id, device.role.value):
    #     if interface.get("role") == "server":
    #         kind = "InfraInterfaceL2"
    #     data = {
    #         "name": interface.get("name"),
    #         "role": interface.get("role"),
    #         "device": device.name.value,
    #         "enabled": True,
    #         "status": "active",
    #         "mtu": 9000,
    #         "description": f"{device.name.value} {interface.get('role')} interface",
    #     }
    #     if interface.get("speed"):
    #         data["speed"] = interface.get("speed")
    #     else:
    #         data["speed"] = 10000
    #     if interface.get("role") == "vtep":
    #         data["role"] = "backbone"
    #     if interface.get("role") == "server":
    #         data["kind"] = "InfraInterfaceL3"
    #         data["l2_mode"] = "trunk"
    #     await self.create_and_save(
    #         object_name=f"{device.name.value}-{interface.get('name')}",
    #         kind_name=kind,
    #         data=data,
    #    )
    # async for node, _ in batch.execute():
    #     if node._schema.default_filter:
    #         accessor = f"{node._schema.default_filter.split('__')[0]}"
    #         print(
    #             f"- Created {node._schema.kind} - {getattr(node, accessor).value}"
    #         )
    #     else:
    #         print(f"- Created {node}")
    #     if interface.get("role") in ["loopback", "management", "vtep"]:
    #         if interface.get("role") == "loopback":
    #             address = f"{str(next(self.pools.get('inband')[0]))}/32"
    #         elif interface.get("role") == "management":
    #             address = f"{str(next(self.pools.get('management')[0]))}/24"
    #         else:
    #             address = f"{str(next(self.pools.get(interface.get('role'))[0]))}/32"
    #         name = f"{device.name.value}-{interface.get('name')}-address"
    #         # print("jestem w ", interface.get("role"), interface.get("name"))
    # #         print(address)
    #         # name = f"{device.name.value}-{interface.get('name')}-address"
    #         data = {
    #             # "ip_namespace": "global",
    #             "vrf": "Management",
    #             "interface": interface_obj.id,
    #             "description": f"{device.name.value} {interface.get('name')}",
    #             "address": address,
    #         }
    #         await self.create_ip(data=data, name=name)

    async def generate_topology_nodes(self, topology, asn):
        """Generate topology nodes."""
        for role in ["spines", "leafs"]:
            device = self.store.get(
                kind="TopologyPhysicalElement", key=f"{topology}-{role}"
            )
            platform = self.store.get(
                key=device.device_type.display_label
            ).platform.display_label
            for sid in range(1, int(device.quantity.value) + 1):
                # is_border: bool = device.border.value
                number = f"0{sid}" if sid < 10 else id
                device_name = f"{topology}-{device.device_role.value}-{number}"
                # print(device.__dict__)
                data_device = {
                    "name": f"{topology}-{device.device_role.value}-{number}",
                    "location": self.store.get(key=topology),
                    "status": "active",
                    "device_type": device.device_type.display_label,
                    "role": device.device_role.value,
                    "asn": self.store.get(key=f"AS{asn}").id,
                    "primary_ip": "management-pool",
                    "platform": platform,
                    "topology": topology,
                }
                device_obj = await self.create_and_save(
                    object_name=device_name,
                    kind_name="InfraDevice",
                    data=data_device,
                    retrieved_on_failure=True,
                )
                # Add device to groups
                platform_group = await self.client.get(
                    name__value=f"{platform.lower().split(' ', 1)[0]}_devices",
                    kind="CoreStandardGroup",
                )
                await platform_group.members.fetch()
                platform_group.members.add(device_obj.id)
                await platform_group.save()
                # await self.create_interfaces(device_obj)

        # print(device.device_type.display_label)
        # print(self.store.get(key=topology, raise_when_missing=False).extract())
        # print(elements)

    async def generate(self, data: dict) -> None:
        """Generate topology."""
        topology = data["TopologyTopology"]["edges"][0]
        topology_name = topology["node"]["name"]["value"]
        vendor = topology["node"]["vendor"]["value"]
        city_name = topology["node"]["location"]["node"]["name"]["value"]
        providers = await self.client.filters(
            "OrganizationGeneric", name__value="Technology Partner"
        )
        self.populate_local_store(objects=providers, key_type="name")
        device_types = await self.client.filters(
            "InfraDeviceType",
            manufacturer__name__value=vendor.capitalize(),
            branch=self.branch,
        )
        self.populate_local_store(objects=device_types, key_type="name")
        # Let's load the all existing topology elements into local store for faster process
        # msp = self.store.get(key=topology_name, raise_when_missing=False)
        # print(msp.get_raw_graphql_data())
        # create site if doesn't exist
        await self.create_sites(
            topology_name,
            city_name,
            topology["node"]["description"]["value"],
        )

        await self.create_asns(topology_name, topology["node"]["asn"]["value"])
        prefixes = {
            network_type: topology["node"][f"{network_type}"]["value"]
            for network_type in ["management", "technical", "customer", "public"]
            if topology["node"][f"{network_type}"]["value"]
        }
        await self.create_subnets(topology_name, prefixes)
        await self.create_topology_elements(
            size=topology["node"]["size"]["value"],
            vendor=vendor,
            topology=topology_name,
            topology_id=topology["node"]["id"],
        )
        # declare pools
        await self.create_pools(topology_name)
        # Create all topology
        # batch = await self.client.create_batch()
        # print(self.store.__dict__)
        # batch.add(
        #         task=self.generate_topology_nodes,
        #         topology=topology_name,
        #     )
        # pool = pools.get('management')[0]
        # ip_mgmt = print(f"{str(next(pools.get('management')[0]))}/24")
        # print(ip_mgmt)
        await self.generate_topology_nodes(
            topology_name, topology["node"]["asn"]["value"]
        )

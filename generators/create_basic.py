import logging
from typing import Dict, Optional
from ipaddress import IPv4Network
from infrahub_sdk import InfrahubBatch, InfrahubClient, NodeStore

from utils import create_and_add_to_batch

# flake8: noqa
# pylint: skip-file

ACCOUNTS = (
    # name, password, type, role
    ("pop-builder", "Script", "Password123", "read-write"),
    ("generator", "Script", "Password123", "read-write"),
    ("CRM Synchronization", "Script", "Password123", "read-write"),
    ("Tomek Zajac", "User", "Password123", "read-write"),
    ("Some User1", "User", "Password123", "read-only"),
    ("Some User2", "User", "Password123", "read-write"),
    ("Some User3", "User", "Password123", "read-write"),
    ("Engineering Team", "User", "Password123", "read-write"),
    ("Architecture Team", "User", "Password123", "read-only"),
    ("Operation Team", "User", "Password123", "read-only"),
)

TAGS = ["blue", "green", "red"]

ORGANIZATIONS = (
    # name, type
    ("Arelion", "provider"),
    ("Colt Technology Services", "provider"),
    ("Verizon Business", "provider"),
    ("GTT Communications", "provider"),
    ("Hurricane Electric", "provider"),
    ("Lumen", "provider"),
    ("Zayo", "provider"),
    ("Equinix", "provider"),
    ("Interxion", "provider"),
    ("PCCW Global", "provider"),
    ("Orange S.A", "provider"),
    ("Tata Communications", "provider"),
    ("Sprint", "provider"),
    ("NTT America", "provider"),
    ("Cogent Communications", "provider"),
    ("Comcast Cable Communication", "provider"),
    ("Telecom Italia Sparkle", "provider"),
    ("AT&T Services", "provider"),
    ("Technology Partner", "provider"),
    ("OE1", "customer"),
    ("ABC", "customer"),
    ("CDE", "customer"),
    ("Juniper", "manufacturer"),
    ("Cisco", "manufacturer"),
    ("Arista", "manufacturer"),
)

SUBNETS_1918 = {
    # prefix, state, owner
    ("10.0.0.0/8", "active"),
    ("172.16.0.0/16", "active"),
    ("192.168.0.0/16", "active"),
}


ASNS = (
    # asn, organization
    (1299, "Arelion"),
    (8220, "Colt Technology Services"),
    (701, "Verizon Business"),
    (3257, "GTT Communications"),
    (6939, "Hurricane Electric"),
    (3356, "Lumen"),
    (6461, "Zayo"),
    (24115, "Equinix"),
    (20710, "Interxion"),
    (3491, "PCCW Global"),
    (5511, "Orange S.A"),
    (6453, "Tata Communications"),
    (1239, "Sprint"),
    (2914, "NTT America"),
    (174, "Cogent Communications"),
    (7922, "Comcast Cable Communication"),
    (6762, "Telecom Italia Sparkle"),
    (7018, "AT&T Services"),
)

VRF = {
    # Name, Description, RD, RT-import, RT-export
    ("Internet", "Internet VRF", "100", "100:100", "100:100"),
    ("Backbone", "Backbone VRF", "101", "101:101", "101:101"),
    ("Management", "OOBA Management VRF", "199", "199:199", "199:199"),
    ("Production", "Production VRF", "200", "200:200", "200:200"),
    ("Test", "Staging VRF", "201", "201:201", "201:201"),
    ("Development", "Development VRF", "202", "202:202", "202:202"),
    ("DMZ", "DMZ VRF", "666", "666:666", "666:666"),
}

ROUTE_TARGETS = {
    # Name, Description
    ("100:100", "Internet VRF Route Target"),
    ("101:101", "Backbone VRF Route Target"),
    ("199:199", "OOBA Management VRF Route Target"),
    ("200:200", "Production Environment VRF Route Target"),
    ("201:201", "Staging Environment VRF Route Target"),
    ("202:202", "Development Environment VRF Route Target"),
    ("666:666", "DMZ VRF Route Target"),
}

PLATFORMS = (
    # name, nornir_platform, napalm_driver, netmiko_device_type, ansible_network_os, containerlab_os
    ("Cisco IOS-XE", "ios", "ios", "cisco_ios", "ios", "ios"),
    ("Cisco IOS-XR", "iosxr", "iosxr", "cisco_xr", "cisco.iosxr.iosxr", "cisco_xrv"),
    ("Cisco NX-OS", "nxos_ssh", "nxos_ssh", "cisco_nxos", "nxos", "cisco_n9kv"),
    (
        "Juniper JunOS",
        "junos",
        "junos",
        "juniper_junos",
        "junos",
        "juniper_vjunosswitch",
    ),
    ("Arista EOS", "eos", "eos", "arista_eos", "eos", "ceos"),
    ("Sonic OS", "dell_sonic", "dell_sonic", "dell_sonic", "dell_sonic", "dell_sonic"),
    ("Linux", "linux", "linux", "linux", "linux", "linux"),
)

DEVICE_TYPES = (
    # name, part_number, height (U), full_depth, platform
    ("MX204", "MX204-HWBASE-AC-FS", 1, False, "Juniper JunOS"),
    ("CCS-720DP-48S-2F", None, 1, False, "Arista EOS"),
    ("DCS-7280DR3-24-F", None, 1, False, "Arista EOS"),
    ("NCS-5501-SE", None, 1, False, "Cisco IOS-XR"),
    ("ASR1002-HX", None, 2, True, "Cisco IOS-XR"),
    ("N9K-C93108TC-FX", "N9K-C93108TC-FX", 1, False, "Cisco NX-OS"),
    ("N9K-C93108TC-FX3", "N9K-C93108TC-FX3", 1, False, "Cisco NX-OS"),
    ("N9K-C93108TC-FX3P", None, 1, False, "Cisco NX-OS"),
    ("N9K-C93120TX", None, 1, False, "Cisco NX-OS"),
    ("N9K-C93128TX", None, 1, False, "Cisco NX-OS"),
    ("N9K-C9316D-GX", None, 1, False, "Cisco NX-OS"),
    ("N9K-C93180YC-EX", None, 1, False, "Cisco NX-OS"),
    ("N9K-C93180YC-FX", None, 1, False, "Cisco NX-OS"),
    ("N9K-C93180YC-FX3", None, 1, False, "Cisco NX-OS"),
    ("N9K-C93180YC-FX3S", None, 1, False, "Cisco NX-OS"),
    ("N9K-C93216TC-FX2", None, 1, False, "Cisco NX-OS"),
    ("N9K-C93240YC-FX2", None, 1, False, "Cisco NX-OS"),
    ("N9K-C9332C", None, 1, False, "Cisco NX-OS"),
    ("N9K-C9332D-GX2B", None, 1, False, "Cisco NX-OS"),
    ("N9K-C9332PQ", None, 1, False, "Cisco NX-OS"),
    ("N9K-C9336C-FX2", None, 1, False, "Cisco NX-OS"),
    ("N9K-C9336PQ", None, 1, False, "Cisco NX-OS"),
    ("N9K-C9348D-GX2A", None, 1, False, "Cisco NX-OS"),
    ("N9K-C9348GC-FX3", None, 1, False, "Cisco NX-OS"),
    ("N9K-C9348GC-FX3PH", None, 1, False, "Cisco NX-OS"),
    ("N9K-C9348GC-FXP", None, 1, False, "Cisco NX-OS"),
    ("N9K-C93600CD-GX", None, 1, False, "Cisco NX-OS"),
    ("N9K-C9364C-GX", None, 1, False, "Cisco NX-OS"),
    ("N9K-C9364C", None, 1, False, "Cisco NX-OS"),
    ("N9K-C9364D-GX2A", None, 1, False, "Cisco NX-OS"),
    ("N9K-C9372PX-E", None, 1, False, "Cisco NX-OS"),
    ("N9K-C9372PX", None, 1, False, "Cisco NX-OS"),
    ("N9K-C9372TX-E", None, 1, False, "Cisco NX-OS"),
    ("N9K-C9372TX", None, 1, False, "Cisco NX-OS"),
    ("N9K-C9396PX", None, 1, False, "Cisco NX-OS"),
)

GROUPS = (
    # name, description
    ("edge_routers", "Edge Routers"),
    ("core_routers", "Core Routers"),
    ("cisco_devices", "Cisco Devices"),
    ("arista_devices", "Arista Devices"),
    ("juniper_devices", "Juniper Devices"),
    ("upstream_interfaces", "Upstream Interface"),
    ("core_interfaces", "Core Interface"),
    ("all_topologies", "All Topologies"),
    ("provisioning_circuits", "Provisioning Circuits"),
)

BGP_PEER_GROUPS = (
    # name, import policy, export policy, local AS, remote AS
    ("POP_INTERNAL", "IMPORT_INTRA_POP", "EXPORT_INTRA_POP", "AS65000", "AS65000"),
    ("POP_GLOBAL", "IMPORT_POP_GLOBAL", "EXPORT_POP_GLOBLA", "AS65000", None),
    ("UPSTREAM_DEFAULT", "IMPORT_UPSTREAM", "EXPORT_PUBLIC_PREFIX", "AS65000", None),
    (
        "UPSTREAM_ARELION",
        "IMPORT_UPSTREAM",
        "EXPORT_PUBLIC_PREFIX",
        "AS65000",
        "AS1299",
    ),
    ("IX_DEFAULT", "IMPORT_IX", "EXPORT_PUBLIC_PREFIX", "AS65000", None),
)

NETWORK_STRATEGY = (
    # Underlay, Overlay, Stategy Type (name and description will be auto-generated)
    ("ebgp-ebgp", "ebgp", "ebgp", "evpn"),
    ("ospf-ebgp", "ospf", "ebgp", "evpn"),
    ("isis-ebgp", "isis", "ebgp", "evpn"),
    ("ospf-ibgp", "ospf", "ibgp", "evpn"),
    ("isis-ibgp", "isis", "ibgp", "evpn"),
)

store = NodeStore()


async def create_basics(client: InfrahubClient, log: logging.Logger, branch: str):
    # Create Batch for Accounts, Platforms, and Standards Groups
    log.info("Creating User Accounts, Subnets, Platforms, and Standard Groups")
    batch = await client.create_batch()
    # ------------------------------------------
    # Create User Accounts
    # ------------------------------------------
    for account in ACCOUNTS:
        data = {
            "name": account[0],
            "password": account[2],
            "type": account[1],
            "role": account[3],
        }
        await create_and_add_to_batch(
            client=client,
            log=log,
            branch=branch,
            object_name=account[0],
            kind_name="CoreAccount",
            data=data,
            store=store,
            batch=batch,
        )

    # ------------------------------------------
    # Create Subnets Accounts
    # ------------------------------------------
    for subnet in SUBNETS_1918:
        # Create Supernet
        supernet_description = f"{IPv4Network(subnet[0]).network_address} Supernet"
        data = {
            "prefix": subnet[0],
            "description": {"value": supernet_description},
            "status": {"value": "active"},
            "role": {"value": "supernet"},
        }
        await create_and_add_to_batch(
            client=client,
            log=log,
            branch=branch,
            object_name=subnet[0],
            kind_name="InfraPrefix",
            data=data,
            store=store,
            batch=batch,
        )

    # ------------------------------------------
    # Create Standard Demo Groups
    # ------------------------------------------
    for group in GROUPS:
        data = {
            "name": group[0],
            "label": group[1],
        }
        await create_and_add_to_batch(
            client=client,
            log=log,
            branch=branch,
            object_name=group[0],
            kind_name="CoreStandardGroup",
            data=data,
            store=store,
            batch=batch,
        )

    async for node, _ in batch.execute():
        accessor = f"{node._schema.default_filter.split('__')[0]}"
        log.info(f"- Created {node._schema.kind} - {getattr(node, accessor).value}")

    # ------------------------------------------
    # Create Organization & Autonomous System
    # ------------------------------------------
    log.info("Creating Organizations, and Autonomous Systems")
    account = store.get("CRM Synchronization", kind="CoreAccount")
    account2 = store.get("Tomek Zajac", kind="CoreAccount")
    # Organization
    batch = await client.create_batch()
    for org in ORGANIZATIONS:
        data_org = {
            "name": {"value": org[0], "is_protected": True},
        }
        await create_and_add_to_batch(
            client=client,
            log=log,
            branch=branch,
            object_name=org[0],
            kind_name=f"Organization{org[1].title()}",
            data=data_org,
            store=store,
            batch=batch,
        )
    async for node, _ in batch.execute():
        accessor = f"{node._schema.default_filter.split('__')[0]}"
        log.info(f"- Created {node._schema.kind} - {getattr(node, accessor).value}")

    # Autonomous System
    organizations_dict = {name: type for name, type in ORGANIZATIONS}
    batch = await client.create_batch()
    for asn in ASNS:
        organization_type = organizations_dict.get(asn[1], None)
        asn_name = f"AS{asn[0]}"
        data_asn = {
            "name": {"value": asn_name, "source": account.id, "owner": account2.id},
            "asn": {"value": asn[0], "source": account.id, "owner": account2.id},
        }
        if organization_type:
            data_asn["description"] = {
                "value": f"{asn_name} for {asn[1]}",
                "source": account.id,
                "owner": account2.id,
            }
            data_asn["organization"] = {
                "id": store.get(
                    kind=f"Organization{organization_type.title()}", key=asn[1]
                ).id,
                "source": account.id,
            }
        else:
            data_asn["description"] = {
                "value": f"{asn_name}",
                "source": account.id,
                "owner": account2.id,
            }
        await create_and_add_to_batch(
            client=client,
            log=log,
            branch=branch,
            object_name=f"AS{asn[0]}",
            kind_name="InfraAutonomousSystem",
            data=data_asn,
            store=store,
            batch=batch,
        )
    # Generate 11 private ASNs for OE1
    for asn in range(65000, 65010):
        data_asn = {
            "name": {"value": f"AS{asn}", "source": account.id, "owner": account2.id},
            "asn": {"value": asn, "source": account.id, "owner": account2.id},
            "description": {
                "value": f"Private ASN {asn_name} for OE1",
                "source": account.id,
                "owner": account2.id,
            },
            "organization": {
                "id": store.get(kind="OrganizationCustomer", key="OE1").id,
                "source": account.id,
            },
        }
        await create_and_add_to_batch(
            client=client,
            log=log,
            branch=branch,
            object_name=f"AS{asn}",
            kind_name="InfraAutonomousSystem",
            data=data_asn,
            store=store,
            batch=batch,
        )
    async for node, _ in batch.execute():
        accessor = f"{node._schema.default_filter.split('__')[0]}"
        log.info(f"- Created {node._schema.kind} - {getattr(node, accessor).value}")

    # ------------------------------------------
    # Create Tags
    # ------------------------------------------
    account = store.get("CRM Synchronization")
    batch = await client.create_batch()
    log.info("Creating Tags")
    for tag in TAGS:
        data = {
            "name": {"value": tag, "source": account.id},
        }
        await create_and_add_to_batch(
            client=client,
            log=log,
            branch=branch,
            object_name=tag,
            kind_name="BuiltinTag",
            data=data,
            store=store,
            batch=batch,
        )
    async for node, _ in batch.execute():
        accessor = f"{node._schema.default_filter.split('__')[0]}"
        log.info(f"- Created {node._schema.kind} - {getattr(node, accessor).value}")

    # ------------------------------------------
    # Create Platform
    # ------------------------------------------
    batch = await client.create_batch()
    for platform in PLATFORMS:
        manufacturer_name = platform[0].split()[0].title()
        manufacturer = store.get(
            key=manufacturer_name,
            kind="OrganizationManufacturer",
            raise_when_missing=False,
        )
        data = {
            "name": platform[0],
            "nornir_platform": platform[1],
            "napalm_driver": platform[2],
            "netmiko_device_type": platform[3],
            "ansible_network_os": platform[4],
            "containerlab_os": platform[5],
        }
        if manufacturer:
            data["manufacturer"] = {"id": manufacturer.id}
        await create_and_add_to_batch(
            client=client,
            log=log,
            branch=branch,
            object_name=platform[0],
            kind_name="InfraPlatform",
            data=data,
            store=store,
            batch=batch,
        )
    async for node, _ in batch.execute():
        accessor = f"{node._schema.default_filter.split('__')[0]}"
        log.info(f"- Created {node._schema.kind} - {getattr(node, accessor).value}")

    # ------------------------------------------
    # Create Standard Device Type
    # ------------------------------------------
    batch = await client.create_batch()
    log.info("Creating Standard Device Type")
    for device_type in DEVICE_TYPES:
        manufacturer_name = device_type[4].split()[0].title()
        manufacturer = store.get(
            key=manufacturer_name,
            kind="OrganizationManufacturer",
            raise_when_missing=False,
        )
        platform_id = store.get(kind="InfraPlatform", key=device_type[4]).id
        data = {
            "name": {"value": device_type[0]},
            "part_number": {"value": device_type[1]},
            "height": {"value": device_type[2]},
            "full_depth": {"value": device_type[3]},
            "platform": {"id": platform_id},
        }
        if manufacturer:
            data["manufacturer"] = {"id": manufacturer.id}
        await create_and_add_to_batch(
            client=client,
            log=log,
            branch=branch,
            object_name=device_type[0],
            kind_name="InfraDeviceType",
            data=data,
            store=store,
            batch=batch,
        )
    async for node, _ in batch.execute():
        accessor = f"{node._schema.default_filter.split('__')[0]}"
        log.info(f"- Created {node._schema.kind} - {getattr(node, accessor).value}")

    # ------------------------------------------
    # Create BGP Peer Groups
    # ------------------------------------------
    log.info(f"Creating BGP Peer Groups")
    account = store.get(key="pop-builder", kind="CoreAccount")
    batch = await client.create_batch()
    for peer_group in BGP_PEER_GROUPS:
        remote_as = remote_as_id = None
        if peer_group[4]:
            remote_as = store.get(
                kind="InfraAutonomousSystem",
                key=peer_group[4],
                raise_when_missing=False,
            )
        local_as = store.get(kind="InfraAutonomousSystem", key=peer_group[3])
        if remote_as:
            remote_as_id = remote_as.id
        if local_as:
            local_as_id = local_as.id

        data = {
            "name": {"value": peer_group[0], "source": account.id},
            "import_policies": {"value": peer_group[1], "source": account.id},
            "export_policies": {"value": peer_group[2], "source": account.id},
            "local_as": local_as_id,
            "remote_as": remote_as_id,
        }
        await create_and_add_to_batch(
            client=client,
            log=log,
            branch=branch,
            object_name=peer_group[0],
            kind_name="InfraBGPPeerGroup",
            data=data,
            store=store,
            batch=batch,
        )
    async for node, _ in batch.execute():
        accessor = f"{node._schema.default_filter.split('__')[0]}"
        log.info(f"- Created {node._schema.kind} - {getattr(node, accessor).value}")

    batch = await client.create_batch()
    log.info(f"Creating Route Targets")
    for route_target in ROUTE_TARGETS:
        rt_name = route_target[0]
        rt_description = route_target[1]
        data = {
            "name": {"value": rt_name, "source": account.id},
            "description": {"value": rt_description, "source": account.id},
        }
        await create_and_add_to_batch(
            client=client,
            log=log,
            branch=branch,
            object_name=rt_name,
            kind_name="InfraRouteTarget",
            data=data,
            store=store,
            batch=batch,
        )

    async for node, _ in batch.execute():
        accessor = f"{node._schema.default_filter.split('__')[0]}"
        log.info(f"- Created {node._schema.kind} - {getattr(node, accessor).value}")

    log.info(f"Creating VRF")
    batch = await client.create_batch()
    for vrf in VRF:
        vrf_name = vrf[0]
        vrf_description = vrf[1]
        vrf_rd = vrf[2]

        vrf_rt_import_obj = store.get(key=vrf[3], kind="InfraRouteTarget")
        vrf_rt_export_obj = store.get(key=vrf[4], kind="InfraRouteTarget")

        data = {
            "name": {"value": vrf_name, "source": account.id},
            "description": {"value": vrf_description, "source": account.id},
            "vrf_rd": {"value": vrf_rd, "source": account.id},
            "import_rt": {"id": vrf_rt_import_obj.id, "source": account.id},
            "export_rt": {"id": vrf_rt_export_obj.id, "source": account.id},
        }
        await create_and_add_to_batch(
            client=client,
            log=log,
            branch=branch,
            object_name=vrf_name,
            kind_name="InfraVRF",
            data=data,
            store=store,
            batch=batch,
        )
    async for node, _ in batch.execute():
        accessor = f"{node._schema.default_filter.split('__')[0]}"
        log.info(f"- Created {node._schema.kind} - {getattr(node, accessor).value}")


async def create_topology_strategies(
    client: InfrahubClient, log: logging.Logger, branch: str
):
    log.info("Creating Network Strategies")
    # Create Network Strategies
    account = store.get(key="pop-builder", kind="CoreAccount")
    batch = await client.create_batch()
    for strategy in NETWORK_STRATEGY:
        name = strategy[0]
        underlay = strategy[1]
        overlay = strategy[2]
        strategy_type = strategy[3]
        description = (
            f"Using {underlay.upper()} as underlay with {overlay.upper()} as overlay"
        )
        data = {
            "name": {"value": name, "source": account.id},
            "description": {"value": description, "source": account.id},
            "underlay": {"value": underlay, "source": account.id},
            "overlay": {"value": overlay, "source": account.id},
        }
        await create_and_add_to_batch(
            client=client,
            log=log,
            branch=branch,
            object_name=name,
            kind_name=f"Topology{strategy_type.upper()}Strategy",
            data=data,
            store=store,
            batch=batch,
        )
    async for node, _ in batch.execute():
        accessor = f"{node._schema.default_filter.split('__')[0]}"
        log.info(f"- Created {node._schema.kind} - {getattr(node, accessor).value}")


# ---------------------------------------------------------------
# Use the `infrahubctl run` command line to execute this script
#
#   infrahubctl run models/infrastructure_edge.py
#
# ---------------------------------------------------------------
async def run(
    client: InfrahubClient, log: logging.Logger, branch: str, **kwargs
) -> None:
    await create_basics(client=client, log=log, branch=branch)
    await create_topology_strategies(client=client, branch=branch, log=log)

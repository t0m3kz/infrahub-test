import logging

from typing import List
from ipaddress import IPv4Network
from infrahub_sdk import InfrahubClient, NodeStore

from utils import create_and_add_to_batch, populate_local_store

# flake8: noqa
# pylint: skip-file

NETWORK_STRATEGY = (
    # Underlay, Overlay, Stategy Type (name and description will be auto-generated)
    ("ebgp-ebgp", "ebgp", "ebgp", "evpn"),
    ("ospf-ebgp", "ospf", "ebgp", "evpn"),
    ("isis-ebgp", "isis", "ebgp", "evpn"),
    ("ospf-ibgp", "ospf", "ibgp", "evpn"),
    ("isis-ibgp", "isis", "ibgp", "evpn"),
)

TOPOLOGY = (
    # name, description, strategy,country, management, internal, data , external
    (
        "eqx-fra",
        "Medium Fabric in Equinix Frankfurt",
        65100,
        "ebgp-ebgp",
        "Frankfurt",
        "medium",
        "cisco",
        "172.16.0.0/23",
        "192.168.0.0/22",
        "10.1.0.0/16",
        "203.0.113.0/28",
    ),
    (
        "eqx-chi",
        "Small Fabric in Equinix Chicago",
        65200,
        "ospf-ibgp",
        "Chicago",
        "small",
        "arista",
        "172.16.4.0/23",
        "192.168.4.0/22",
        "10.2.0.0/16",
    ),
)


store = NodeStore()


async def create_topology(client: InfrahubClient, log: logging.Logger, branch: str):
    # ------------------------------------------
    # Create Topology
    # ------------------------------------------
    log.info("Creating Topologies")
    # Create Topology Group
    batch = await client.create_batch()
    for topology in TOPOLOGY:
        group_name = f"{topology[0]}_topology"
        data = {
            "name": group_name,
        }
        await create_and_add_to_batch(
            client=client,
            log=log,
            branch=branch,
            object_name=group_name,
            kind_name="CoreStandardGroup",
            data=data,
            store=store,
            batch=batch,
        )
    async for node, _ in batch.execute():
        accessor = f"{node._schema.default_filter.split('__')[0]}"
        log.info(f"- Created {node._schema.kind} - {getattr(node, accessor).value}")

    # Create Topology
    account = store.get(key="pop-builder", kind="CoreAccount")
    batch = await client.create_batch()
    strategy_dict = {name: type for name, underlay, overlay, type in NETWORK_STRATEGY}
    for topology in TOPOLOGY:
        topology_strategy = topology[3]
        topology_location = topology[4]
        data = {
            "name": {"value": topology[0], "source": account.id},
            "description": {"value": topology[1], "source": account.id},
            "asn": topology[2],
            "size": topology[5],
            "vendor": topology[6],
            "management": topology[7],
            "technical": topology[8],
            "customer": topology[9],
        }
        if len(topology) > 10:
            data.update({"public": topology[10]})
        if topology_strategy:
            strategy_type = strategy_dict.get(topology[3], None).upper()
            data["strategy"] = store.get(
                kind=f"Topology{strategy_type}Strategy", key=topology_strategy
            ).id
        if topology_location:
            topology_location_object = store.get(key=topology[4])
            if topology_location_object:
                data["location"] = {"id": topology_location_object.id}
        await create_and_add_to_batch(
            client=client,
            log=log,
            branch=branch,
            object_name=topology[0],
            kind_name="TopologyTopology",
            data=data,
            store=store,
            batch=batch,
        )
    async for node, _ in batch.execute():
        accessor = f"{node._schema.default_filter.split('__')[0]}"
        log.info(f"- Created {node._schema.kind} - {getattr(node, accessor).value}")

    batch = await client.create_batch()
    for topology in TOPOLOGY:
        # Add Topology to Topology Group
        topology_name = topology[0]
        topology_group = await client.get(
            name__value=f"{topology_name}_topology", kind="CoreStandardGroup"
        )
        topology_obj = await client.get(
            name__value=topology_name, kind="TopologyTopology"
        )
        await topology_group.members.fetch()
        topology_group.members.add(topology_obj.id)
        await topology_group.save()
        log.info(
            f"- Add {topology_name} to {topology_group.name.value} CoreStandardGroup"
        )

        topology_object = store.get(key=topology_name, kind="TopologyTopology")
        if topology[3]:
            topology_location_object = store.get(key=topology[4])
            if topology_location_object:
                topology_object.location = topology_location_object
                await topology_object.save()
            log.info(
                f"- Add {topology_name} to {topology_location_object.name.value} Location"
            )

    # Add Topologies to Topology Summary Group
    all_topologies_group = await client.get(
        name__value=f"all_topologies", kind="CoreStandardGroup"
    )
    await all_topologies_group.members.fetch()
    for topology in TOPOLOGY:
        topology_name = topology[0]
        topology_obj = await client.get(
            name__value=topology_name, kind="TopologyTopology"
        )
        all_topologies_group.members.add(topology_obj.id)
        log.info(
            f"- Add {topology_name} to {topology_group.name.value} CoreStandardGroup"
        )
    await all_topologies_group.save()

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
    log.info("Retrieving objects from Infrahub")
    try:
        accounts = await client.all("CoreAccount")
        populate_local_store(objects=accounts, key_type="name", store=store)
        tenants = await client.all("OrganizationCustomer")
        topology_strategies = await client.all("TopologyNetworkStrategy")
        populate_local_store(objects=topology_strategies, key_type="name", store=store)
        populate_local_store(objects=tenants, key_type="name", store=store)
        providers = await client.all("OrganizationProvider")
        populate_local_store(objects=providers, key_type="name", store=store)
        manufacturers = await client.all("OrganizationManufacturer")
        populate_local_store(objects=manufacturers, key_type="name", store=store)
        autonomous_systems = await client.all("InfraAutonomousSystem")
        populate_local_store(objects=autonomous_systems, key_type="name", store=store)
        platforms = await client.all("InfraPlatform")
        populate_local_store(objects=platforms, key_type="name", store=store)
        device_types = await client.all("InfraDeviceType")
        populate_local_store(objects=device_types, key_type="name", store=store)
        locations = await client.all("LocationGeneric")
        populate_local_store(objects=locations, key_type="name", store=store)

    except Exception as e:
        log.error(f"Fail to populate due to {e}")
        exit(1)

    await create_topology(client=client, branch=branch, log=log)

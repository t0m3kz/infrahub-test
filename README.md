# InfraHub test repo

## Steps

```shell
poetry run infrahubctl run generators/create_basic.py
poetry run infrahubctl run generators/create_location.py
poetry run infrahubctl run generators/create_topology.py

poetry run infrahubctl run generators/generate_topology.py name=eqx-chi
poetry run infrahubctl render device_arista device=eqx-chi-leaf1
```

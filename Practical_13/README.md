# Practical 13 - Security, Monitoring, Snapshots and Failure Analysis

A hands-on Elasticsearch operations and security lab against a dedicated
secured single-node cluster on `http://127.0.0.1:9201`. It creates users and
roles, restricts index access, issues an API key, inspects cluster/node/JVM
statistics, configures slow logs, creates and restores a filesystem snapshot,
diagnoses an unassigned replica shard, and reproduces indexing failures.

The lab uses its own Docker Compose project, data volume, container, and port,
so the unsecured Practical 9-12 cluster on port `9200` is not modified.

**Environment**

- Elasticsearch 9.2.0 at `http://127.0.0.1:9201` (secured, HTTP auth enabled)
- Cluster `p13-secured-cluster`, node `p13-node`, single node, 512 MB heap
- Python client `elasticsearch 9.5.1`, kernel `es`
- Dataset: 1,000 public and 500 private deterministic synthetic events, seed 42
- Snapshot repository: shared filesystem at `/usr/share/elasticsearch/snapshots`

All event data is synthetic.

## Files

| File | Purpose |
|---|---|
| `generate_data.py` | Deterministic generator for public and private events |
| `mapping.json` | Strict mappings/settings for the event and failure-demo indices |
| `docker-compose.yaml` | Secured Elasticsearch service on port `9201` |
| `config/elasticsearch.yml` | Cluster name, single-node discovery, security, `path.repo` |
| `practical_13.ipynb` | Executed Tasks 1-14 with assertions |
| `artifacts/security_report.json` | Security, access, cluster, node, JVM, and slow-log data |
| `artifacts/operations_report.json` | Snapshot, restore, unassigned-shard, and failure data |
| `snapshots/.gitkeep` | Keeps the (ignored) snapshot mount directory in git |
| `README.md` | This summary |

Generated event data is not stored as raw files. It can optionally be written as
NDJSON:

```powershell
..\.venv\Scripts\python.exe generate_data.py `
  --output data/public.ndjson `
  --private-output data/private.ndjson
```

## Setup

Start the secured node:

```powershell
cd "C:\D-Drive\Elastic Search Practicals\Practical_13"
docker compose up -d
docker ps --filter name=p13-elasticsearch
```

Then execute the notebook:

```powershell
..\.venv\Scripts\python.exe -m nbconvert --to notebook --execute --inplace `
  --ExecutePreprocessor.kernel_name=es --ExecutePreprocessor.timeout=600 practical_13.ipynb
```

Stop the stack without deleting its data:

```powershell
docker compose down
```

Add `--volumes` only when a clean cluster is actually wanted.

## Security model

Security is enabled, but HTTP and transport TLS are deliberately disabled for
this local lab so the examples stay readable. Authentication and authorization
are still enforced:

```yaml
xpack.security.enabled: true
xpack.security.http.ssl.enabled: false
xpack.security.transport.ssl.enabled: false
xpack.security.autoconfiguration.enabled: false
```

- Administrative calls authenticate as `elastic` with the Compose password.
- Anonymous calls are rejected with HTTP 401.
- A separate analyst user is tested against allowed and denied indices.
- The generated API key's encoded secret is used for live requests but is never
  printed or written to an artifact.

Do not copy this TLS configuration to a shared or production network.

## Dataset and mappings

### `p13-public-events` / `p13-private-events`

One shard, zero replicas, `dynamic: strict`, refresh disabled during the bulk
load and restored to `1s` afterward.

| Field | Type | Notes |
|---|---|---|
| `event_id` | `keyword` | `PUB-000001` or `PRV-000001` |
| `created_at` | `date` | ISO-8601 UTC |
| `service` | `keyword` | billing, catalog, identity, search, notifications |
| `level` | `keyword` | info, warn, error |
| `amount` | `integer` | Synthetic amount |
| `message` | `text` | Searchable message |
| `visibility` | `keyword` | public or private |

### `p13-failure-demo`

One shard, zero replicas, `dynamic: strict`, with only `event_id` (`keyword`) and
`amount` (`integer`). Used to trigger controlled indexing failures.

## Task results

### 1. Configure a secured Elasticsearch environment

The live check reported:

```json
{
  "url": "http://127.0.0.1:9201",
  "cluster_name": "p13-secured-cluster",
  "node_name": "p13-node",
  "version": "9.2.0",
  "authenticated_user": "elastic",
  "authenticated_roles": ["superuser"],
  "anonymous_status": 401
}
```

The authenticated admin succeeded while the unauthenticated client was rejected
with **401**.

### 2. Create a user

`p13_analyst` was created with no roles and `enabled: true`, then inspected to
confirm the empty role list:

```json
{
  "username": "p13_analyst",
  "roles": [],
  "full_name": "Practical 13 Analyst",
  "email": "p13-analyst@example.test",
  "enabled": true
}
```

### 3. Create a role

`p13_public_reader` grants cluster `monitor` and read-only access to the
`p13-public-*` index pattern:

```json
{
  "cluster": ["monitor"],
  "indices": [
    {
      "names": ["p13-public-*"],
      "privileges": ["read", "view_index_metadata"]
    }
  ]
}
```

The role was then assigned to `p13_analyst`.

### 4. Restrict index access

`p13-public-events` and `p13-private-events` were created with the same strict
mapping. Bulk loads completed with zero errors:

| Index | Documents | Load time | Throughput |
|---|---:|---:|---:|
| `p13-public-events` | 1,000 | 3.687 s | 271.3 docs/s |
| `p13-private-events` | 500 | 0.672 s | 744.5 docs/s |

Results as `p13_analyst`:

| Check | Result |
|---|---|
| Count on `p13-public-events` | 1,000 |
| Count on `p13-private-events` | HTTP 403 |

The denial is an explicit `security_exception`: the analyst has
`p13_public_reader` only, and that role does not grant access to the private
index.

### 5. Generate an API key

A one-day API key was created with a role descriptor limited to `p13-public-*`:

| Field | Value |
|---|---|
| Name | `p13-public-reader-<timestamp>` |
| ID | Returned by Elasticsearch |
| Expiration | Returned as epoch milliseconds |
| Public index count | 1,000 |
| Private index status | HTTP 403 |
| Encoded secret stored | `false` |

The encoded key authenticated successfully for the allowed index and was denied
for the private index.

### 6. Inspect cluster health

```text
status: green
number_of_nodes: 1
active_primary_shards: 8
unassigned_shards: 0
active_shards_percent: 100.0
```

The single-node cluster is green with one node and no unassigned shards.

### 7. Inspect node statistics

Selected values from `_nodes/stats`:

| Area | Metric | Value |
|---|---|---:|
| OS | CPU | 34% |
| OS | Memory used | 98% (host-level) |
| OS | Swap used | 238,858,240 bytes |
| Process | Open file descriptors | 629 / 1,048,576 |
| Process | CPU | 18% |
| Indices | Documents | 2,543 |
| Indices | Store | 374,479 bytes |
| Indices | Search query total | 24 |
| Indices | Indexing total | 3,063 |
| Thread pools | `search`/`write`/`get` queue and rejections | 0 |

The document total includes the restored index and the small demo indices.

### 8. Investigate JVM memory usage

| Metric | Value |
|---|---:|
| Heap used | 130,617,600 bytes |
| Heap max | 536,870,912 bytes (512 MB) |
| Heap used | 24.33% |
| Non-heap used | 238,065,312 bytes |
| Old-generation used | 115,265,848 bytes |
| Young GC | 44 collections, 24,027 ms |
| G1 concurrent GC | 10 collections, 21,309 ms |
| Old GC | 0 collections |
| Uptime | 1,578,446 ms |

Heap use is well below the configured maximum and there have been no
old-generation collections. The 98% OS memory figure is the container host's
memory, not Elasticsearch heap pressure.

### 9. Configure slow logs

Search and indexing slow logs were set to zero-millisecond thresholds on
`p13-public-events` and the temporary `p13-slowlog-demo` index:

```json
{
  "index.search.slowlog.threshold.query.warn": "0ms",
  "index.search.slowlog.threshold.query.info": "0ms",
  "index.search.slowlog.threshold.fetch.warn": "0ms",
  "index.search.slowlog.threshold.fetch.info": "0ms",
  "index.indexing.slowlog.threshold.index.warn": "0ms",
  "index.indexing.slowlog.threshold.index.info": "0ms"
}
```

The container writes JSON slow-log records to stdout, so the notebook reads them
with `docker logs`. Captured examples:

| Type | Logger | Took | Source |
|---|---|---|---:|
| Search query | `index.search.slowlog.query` | 25.4 ms | `match` on `message` |
| Search fetch | `index.search.slowlog.fetch` | 11.6 ms | `size: 5` |
| Indexing | `index.indexing.slowlog.index` | 228.9 µs | demo event |

The run found six search and five indexing records in the five-minute Docker log
window; the last three of each type are stored in the artifact. The temporary
index is deleted afterward.

Note: Elasticsearch 9 removed the `index.search.slowlog.level` and
`index.indexing.slowlog.level` settings. Setting them raises
`illegal_argument_exception: unknown setting`. Only the threshold settings are
used here.

### 10. Create a snapshot repository

```json
{
  "type": "fs",
  "settings": {
    "compress": "true",
    "location": "/usr/share/elasticsearch/snapshots"
  }
}
```

The location is mounted from `Practical_13/snapshots` and declared in
`path.repo`. Snapshot contents are gitignored.

### 11. Create a snapshot

| Field | Value |
|---|---|
| Repository | `p13-snapshot-repo` |
| Snapshot | `p13-public-snapshot` |
| Indices | `p13-public-events` |
| State | `SUCCESS` |
| Shards | 1 total, 1 successful, 0 failed |
| Include global state | `false` |
| Client-observed elapsed | 3.232 s |

Excluding global state keeps security metadata and system indices out of the
snapshot.

### 12. Restore a snapshot

The snapshot was restored under a new name with a rename pattern:

| Field | Value |
|---|---|
| Source | `p13-public-events` |
| Destination | `p13-public-events-restored` |
| Documents | 1,000 |
| Source documents | 1,000 |
| Mapping `dynamic` | `strict` |
| Client-observed elapsed | 4.817 s |

Restoring to a new index name avoids overwriting the live source.

### 13. Investigate an unassigned shard

`p13-unassigned-demo` was created with one shard and one replica on a
single-node cluster:

| Stage | Health | Unassigned | Active shards |
|---|---|---|---:|
| With replica | `yellow` | 1 | 50.0% |
| After replicas set to 0 | `green` | 0 | 100.0% |

`_cluster/allocation/explain` reported `can_allocate: "no"` with the blocking
decider:

```json
{
  "decider": "same_shard",
  "decision": "NO",
  "explanation": "a copy of this shard is already allocated to this node ..."
}
```

A single node cannot host both the primary and its replica. Setting
`index.number_of_replicas` to `0` resolved the condition.

### 14. Investigate an indexing failure

Both controlled writes to `p13-failure-demo` returned HTTP 400 and were not
stored.

| Case | Error type | Cause |
|---|---|---|
| `"not-a-number"` in an `integer` field | `document_parsing_exception` | `number_format_exception` |
| Unknown field under `dynamic: strict` | `strict_dynamic_mapping_exception` | Field not in the mapping |

Document count stayed at **1** after both failures and became **2** after a
corrected document was indexed. The fixes are to send a numeric amount or add an
explicit mapping for the new field.

## Artifacts

| File | Contents |
|---|---|
| `artifacts/security_report.json` | Environment, user, role, index access, API key metadata, cluster health, node stats, JVM, slow logs |
| `artifacts/operations_report.json` | Snapshot repository, snapshot, restore, unassigned-shard analysis, indexing failures |

The API key's `encoded` secret is intentionally omitted from every report.

## Verification

The executed notebook asserts:

- The cluster is `p13-secured-cluster`, authenticated as `elastic`, and
  anonymous access returns 401.
- The analyst user starts with no roles and receives `p13_public_reader`.
- The role grants only `p13-public-*` while `p13-private-events` returns 403.
- The API key authenticates for public data and is denied for private data.
- Cluster health is green with one node and no unassigned shards.
- Node, JVM, and thread-pool statistics are collected.
- All six slow-log thresholds are present and both log types are captured.
- The repository is type `fs`, the snapshot is `SUCCESS` with zero failed
  shards and no global state, and the restored count equals the source count.
- The unassigned replica explains `same_shard`, and health becomes green after
  setting replicas to zero.
- Both indexing failures return 400, no failed document is stored, and the
  corrected document is stored.
- Both JSON artifacts are written and contain no API key secret.

Execution result: **32 cells (15 code, 17 markdown), 0 errors, all outputs stored.**

Live verification after execution:

```text
cluster: p13-secured-cluster (green, 1 node)
p13-public-events: 1000 documents
p13-private-events: 500 documents
p13-public-events-restored: 1000 documents
snapshot: p13-public-snapshot SUCCESS
```

## Caveats

- HTTP and transport TLS are disabled for local readability. Authentication and
  authorization are still active, but this is not a production configuration.
- The Compose file contains a lab-only `elastic` password. Do not reuse it.
- Slow-log evidence is read from container stdout via `docker logs`; log
  retention and the `--since` window affect how many entries are visible.
- Snapshot and restore timings are from one local Docker node and vary between
  runs.
- The 98% OS memory figure is host memory, not JVM heap. The JVM heap is capped
  at 512 MB and stayed below 25% during the run.
- The unassigned-shard failure is deliberate; one shard plus one replica cannot
  be fully allocated on a single node.
- Demo indices (`p13-failure-demo`, `p13-unassigned-demo`,
  `p13-public-events-restored`) are left in place so the results can be
  inspected; rerunning the notebook deletes and recreates them.

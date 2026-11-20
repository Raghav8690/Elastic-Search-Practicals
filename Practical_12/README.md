# Practical 12 - Geospatial Queries

A hands-on Elasticsearch geospatial lab against the local single-node cluster.
It creates a `geo_point` index with 10,000 synthetic places around central
London, loads five district polygons into a separate `geo_shape` index, and
demonstrates radius, bounding-box, distance-sort, geo-distance aggregation,
`geo_shape`, and polygon queries.

**Environment**

- Elasticsearch 9.2.0 at `http://127.0.0.1:9200`
- Kibana 9.2.0 at `http://127.0.0.1:5601`
- Python client `elasticsearch 9.5.1`, kernel `es`
- Reference point: `51.5074, -0.1278` (central London)
- Dataset: 10,000 deterministic synthetic places, seed 42

All place names and coordinates are synthetic. They do not represent real
businesses.

## Files

| File | Purpose |
|---|---|
| `generate_data.py` | Deterministic generator for 10,000 places and 5 district polygons |
| `mapping.json` | Strict mappings/settings for `p12-locations` and `p12-districts` |
| `practical_12.ipynb` | Executed Tasks 1-7 with assertions |
| `artifacts/geo_report.json` | Mappings, load metrics, query results, samples, aggregation buckets |
| `artifacts/benchmark.json` | Ten-run query timing summary |
| `README.md` | This summary |

The generated datasets are not stored as raw files. They can optionally be
written as NDJSON:

```powershell
..\.venv\Scripts\python.exe generate_data.py `
  --output data/places.ndjson `
  --districts-output data/districts.ndjson
```

## Dataset and mappings

### `p12-locations`

One shard, zero replicas, `dynamic: strict`, refresh disabled during the bulk
load and restored to `1s` afterward.

| Field | Type | Notes |
|---|---|---|
| `place_id` | `keyword` | `PLC-000001` ... `PLC-010000` |
| `name` | `keyword` | Synthetic place name |
| `category` | `keyword` | cafe, restaurant, pharmacy, grocery, bank, gym, library, hotel |
| `latitude` | `double` | Numeric latitude |
| `longitude` | `double` | Numeric longitude |
| `location` | `geo_point` | Object form `{"lat": ..., "lon": ...}` |
| `rating` | `half_float` | 3.0-5.0 |
| `capacity` | `integer` | 5-500 |
| `open_now` | `boolean` | Synthetic status |

### `p12-districts`

One shard, zero replicas, `dynamic: strict`.

| Field | Type | Notes |
|---|---|---|
| `district_id` | `keyword` | `district-central`, etc. |
| `name` | `keyword` | Central, North, South, East, West |
| `center` | `geo_point` | Representative point |
| `boundary` | `geo_shape` | Closed GeoJSON polygon |

The five districts are non-overlapping rectangles around the reference point.
GeoJSON coordinates use `[longitude, latitude]` order. Polygon rings are closed
and counter-clockwise.

The generated places are uniformly distributed inside an approximate 20 km
radius disk. The actual maximum haversine distance in the dataset is
**19.9818 km**, so every document falls inside the final open-ended `20+`
aggregation range.

## Setup

```powershell
cd "C:\D-Drive\Elastic Search Practicals\Practical_12"
..\.venv\Scripts\python.exe -m nbconvert --to notebook --execute --inplace `
  --ExecutePreprocessor.kernel_name=es --ExecutePreprocessor.timeout=600 practical_12.ipynb
```

The notebook deletes and recreates only `p12-locations` and `p12-districts`.
It leaves the indices from Practicals 9-11 untouched.

## Task results

### 1. Create an index with `geo_point` mapping

`p12-locations` was created with one shard, zero replicas, and a strict mapping.
The relevant mapping is:

```json
{
  "location": {"type": "geo_point"},
  "latitude": {"type": "double"},
  "longitude": {"type": "double"}
}
```

The notebook asserts that `location.type` is `geo_point`, that the numeric
latitude/longitude fields exist, and that the mapping is strict.

### 2. Insert records containing latitude and longitude

The bulk load indexed all **10,000** documents with zero errors:

| Metric | Value |
|---|---:|
| Documents | 10,000 |
| Errors | 0 |
| Load time | 3.049 s |
| Throughput | 3,279.6 docs/s |
| Primary store | 1,528,238 bytes |
| Segments | 1 |

The first document is `PLC-000001` (`Islington Bank 00001`) at
`51.529884, 0.100176`. Its `location` object matches its numeric latitude and
longitude exactly.

### 3. Search within a 5 km radius

Query:

```json
{
  "geo_distance": {
    "distance": "5km",
    "location": {"lat": 51.5074, "lon": -0.1278}
  }
}
```

| Metric | Value |
|---|---:|
| Matches | 660 |
| Percentage of dataset | 6.6% |
| Maximum haversine distance | 4.9907 km |
| Query time | 0.0929 s |

The notebook retrieves all 660 hits and independently checks every hit with a
haversine calculation. No hit exceeds 5 km.

Nearest five results:

| Place | Category | Distance |
|---|---|---:|
| `PLC-007804` Thames Bank 07804 | bank | 0.222 km |
| `PLC-000562` Hampstead Bank 00562 | bank | 0.260 km |
| `PLC-000731` Richmond Bank 00731 | bank | 0.279 km |
| `PLC-005197` Shoreditch Pharmacy 05197 | pharmacy | 0.321 km |
| `PLC-002575` Camden Grocery 02575 | grocery | 0.412 km |

### 4. Search within a geographical bounding box

Query:

```json
{
  "geo_bounding_box": {
    "location": {
      "top_left": {"lat": 51.54, "lon": -0.18},
      "bottom_right": {"lat": 51.48, "lon": -0.07}
    }
  }
}
```

| Metric | Value |
|---|---:|
| Matches | 425 |
| Returned | 425 |
| All inside the box | true |
| Query time | 0.0484 s |

The notebook checks each returned document against its numeric latitude and
longitude, so the assertion does not rely solely on the query result.

### 5. Sort results by distance

Sort specification:

```json
[
  {
    "_geo_distance": {
      "location": {"lat": 51.5074, "lon": -0.1278},
      "order": "asc",
      "unit": "km",
      "mode": "min"
    }
  }
]
```

The nearest ten distances were:

```text
0.2219, 0.2603, 0.2794, 0.3213, 0.4115,
0.5193, 0.5628, 0.5802, 0.6090, 0.6950 km
```

The distances are nondecreasing, and each `_geo_distance` sort value matches an
independent haversine calculation within 0.02 km. The nearest place is
`PLC-007804` at 0.222 km.

### 6. Implement geo-distance aggregations

Aggregation from the reference point:

```json
{
  "geo_distance": {
    "field": "location",
    "origin": {"lat": 51.5074, "lon": -0.1278},
    "unit": "km",
    "ranges": [
      {"to": 1},
      {"from": 1, "to": 2},
      {"from": 2, "to": 5},
      {"from": 5, "to": 10},
      {"from": 10, "to": 20},
      {"from": 20}
    ]
  }
}
```

| Range | Documents |
|---|---:|
| 0-1 km | 21 |
| 1-2 km | 83 |
| 2-5 km | 556 |
| 5-10 km | 1,794 |
| 10-20 km | 7,546 |
| 20+ km | 0 |
| **Total** | **10,000** |

The `0-1`, `1-2`, and `2-5` buckets sum to **660**, exactly matching the
`geo_distance` query count. The final open-ended bucket is empty because the
whole dataset lies within 20 km.

### 7. Explore `geo_shape` and polygon queries

`p12-districts` contains five documents with `boundary.type == "geo_shape"`.
The district load completed in 0.19 s with zero errors; its primary store is
7,073 bytes.

#### Point inside a shape

Query shape:

```json
{"type": "point", "coordinates": [-0.1278, 51.5074]}
```

The `geo_shape` query returned exactly **Central**. This verifies that the
reference point lies inside the Central district polygon and that the GeoJSON
longitude/latitude order is correct.

#### Polygon intersecting shapes

The inner envelope spans the Central and East interiors without touching the
North or South boundaries:

```json
{
  "type": "polygon",
  "coordinates": [[
    [-0.145, 51.495],
    [-0.005, 51.495],
    [-0.005, 51.525],
    [-0.145, 51.525],
    [-0.145, 51.495]
  ]]
}
```

The `geo_shape` query returned **Central** and **East** only, as expected.

#### `geo_polygon` against points

The Central polygon was converted to `geo_polygon` points and applied to
`p12-locations`:

| Source | Count |
|---|---:|
| Elasticsearch `geo_polygon` | 126 |
| Independent Python point-in-rectangle check | 126 |

The exact agreement confirms the polygon query is returning the points inside
the Central boundary.

### Query timing summary

Ten iterations per query; times include local HTTP/client overhead and are not a
production benchmark.

| Query | p50 | p95 | Hits |
|---|---:|---:|---:|
| 5 km radius | 52.362 ms | 80.181 ms | 660 |
| Bounding box | 50.144 ms | 56.117 ms | 425 |
| Distance sort | 56.482 ms | 74.614 ms | 10,000 |
| Geo-distance aggregation | 50.327 ms | 84.328 ms | 10,000 |
| `geo_shape` point | 47.755 ms | 76.414 ms | 1 |
| `geo_shape` polygon | 52.822 ms | 242.141 ms | 2 |
| `geo_polygon` | 64.631 ms | 76.849 ms | 126 |

The p50 values sit near the local HTTP overhead floor. The `geo_shape` polygon
p95 spike is host noise rather than a stable property of the query.

## Verification

The executed notebook asserts:

- The `location` mapping is `geo_point` and the `boundary` mapping is `geo_shape`.
- Exactly 10,000 locations and 5 districts are loaded with zero errors.
- Every 5 km result is within 5 km according to haversine.
- Every bounding-box result has coordinates inside the requested box.
- Distance-sort values are ascending and match haversine.
- Aggregation buckets sum to 10,000 and the within-5-km buckets equal the
  radius query count.
- The GeoJSON point intersects only Central.
- The inner polygon intersects only Central and East.
- `geo_polygon` matches the independent point-in-polygon count.
- Both JSON artifacts are written.

Execution result: **23 cells (12 code, 11 markdown), 0 errors, all outputs stored.**

Live verification after execution:

```text
p12-locations: 10000 documents
p12-districts: 5 documents
location: geo_point
boundary: geo_shape
```

## Caveats

- All timings are from one local Docker node with zero replicas and shared
  cluster load.
- Query p50 includes Python client and HTTP overhead; it is not pure Elasticsearch
  search time.
- The 20 km distribution is generated with a simple local projection and rounded
  coordinates. The actual maximum distance is checked after generation and is
  19.9818 km.
- The district polygons are hand-authored synthetic rectangles, not real London
  administrative boundaries.
- GeoJSON coordinates are `[longitude, latitude]`; reversing them is a common
  source of incorrect shape results.
- The `20+` aggregation bucket being empty is expected for this dataset, not an
  error.

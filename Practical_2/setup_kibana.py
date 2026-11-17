"""Create a Kibana Data View + visualizations + dashboard for the employees index.

Uses the Kibana REST API via ``requests`` so no manual clicking is required:

  1. Ensures a data view named ``employees`` exists (index pattern ``employees``,
     time field ``joining_date``).
  2. Imports a set of saved objects (3 Lens charts + 1 metric + a dashboard)
     through ``POST /api/saved_objects/_import?overwrite=true``.

The script is idempotent: re-running overwrites the same saved objects.

Usage:
    python setup_kibana.py
"""

import json
import os

import requests

KIBANA_URL = os.getenv("KIBANA_URL", "http://127.0.0.1:5601").rstrip("/")
DATA_VIEW_TITLE = "employees"
TIME_FIELD = "joining_date"
HEADERS = {"kbn-xsrf": "true"}

AVG_SALARY_ID = "emp-viz-avg-salary-by-dept"
HEADCOUNT_ID = "emp-viz-headcount-by-city"
HIRES_TREND_ID = "emp-viz-hires-over-time"
TOTAL_ID = "emp-viz-total-employees"
DASHBOARD_ID = "emp-dashboard-overview"


def api(method, path, **kwargs):
    last_error = None
    for _ in range(3):
        try:
            resp = requests.request(
                method, KIBANA_URL + path, headers=HEADERS, timeout=180, **kwargs
            )
            break
        except requests.RequestException as exc:
            last_error = exc
    else:
        raise RuntimeError(f"{method} {path} -> request failed: {last_error}")

    if resp.status_code >= 400:
        raise RuntimeError(f"{method} {path} -> {resp.status_code}: {resp.text[:600]}")
    if not resp.content:
        return None
    return resp.json()


def wait_for_kibana():
    import time

    for attempt in range(20):
        try:
            requests.get(f"{KIBANA_URL}/api/status", timeout=15).raise_for_status()
            return True
        except requests.RequestException as exc:
            if attempt == 0:
                print(f"[.] Waiting for Kibana at {KIBANA_URL} ... ({exc})")
            time.sleep(5)
    print(f"[!] Cannot reach Kibana at {KIBANA_URL}")
    print("    Start the stack first:  docker compose up -d   (in Practical_1)")
    return False


def ensure_data_view():
    existing = api("GET", "/api/data_views")
    for view in existing.get("data_view", []):
        if view.get("title") == DATA_VIEW_TITLE:
            print(f"Data view '{DATA_VIEW_TITLE}' already exists (id={view['id']}).")
            return view["id"]

    body = {
        "data_view": {
            "title": DATA_VIEW_TITLE,
            "name": DATA_VIEW_TITLE,
            "timeFieldName": TIME_FIELD,
        }
    }
    created = api("POST", "/api/data_views/data_view", json=body)
    view_id = created["data_view"]["id"]
    print(f"Created data view '{DATA_VIEW_TITLE}' (id={view_id}).")
    return view_id


def ref_name(layer_id="layer1"):
    return f"indexpattern-datasource-layer-{layer_id}"


def terms_column(label, field):
    return {
        "label": label,
        "dataType": "string",
        "operationType": "terms",
        "scale": "ordinal",
        "sourceField": field,
        "isBucketed": True,
        "params": {
            "size": 20,
            "orderBy": {"type": "column", "columnId": "y"},
            "orderDirection": "desc",
            "otherBucket": False,
            "missingBucket": False,
        },
    }


def metric_column(label, field, operation="average"):
    return {
        "label": label,
        "dataType": "number",
        "operationType": operation,
        "scale": "ratio",
        "sourceField": field,
        "isBucketed": False,
        "params": {"emptyAsNull": True},
    }


def count_column(label="Count of records"):
    return {
        "label": label,
        "dataType": "number",
        "operationType": "count",
        "scale": "ratio",
        "isBucketed": False,
        "sourceField": "___records___",
        "params": {"emptyAsNull": False},
    }


def date_histogram_column(label="joining_date"):
    return {
        "label": label,
        "dataType": "date",
        "operationType": "date_histogram",
        "scale": "interval",
        "sourceField": TIME_FIELD,
        "isBucketed": True,
        "params": {"interval": "auto", "includeEmptyRows": True, "dropPartials": False},
    }


def xy_object(obj_id, title, x_column, y_column, series_type="bar_stacked"):
    datasource = {
        "formBased": {
            "layers": {
                "layer1": {
                    "layerId": "layer1",
                    "layerType": "data",
                    "columns": {"x": x_column, "y": y_column},
                    "columnOrder": ["x", "y"],
                    "incompleteColumns": {},
                    "indexPatternId": "__DATA_VIEW_ID__",
                }
            }
        }
    }
    visualization = {
        "legend": {"isVisible": True, "position": "right"},
        "valueLabels": "hide",
        "preferredSeriesType": series_type,
        "layers": [
            {
                "layerId": "layer1",
                "layerType": "data",
                "accessors": ["y"],
                "xAccessor": "x",
                "position": "top",
                "seriesType": series_type,
                "showGridlines": False,
            }
        ],
        "axisTitlesVisibilitySettings": {"x": True, "yLeft": True, "yRight": True},
        "fittingFunction": "None",
        "gridlinesVisibilitySettings": {"x": True, "yLeft": True, "yRight": True},
        "tickLabelsVisibilitySettings": {"x": True, "yLeft": True, "yRight": True},
        "yLeftExtent": {"mode": "full"},
        "yRightExtent": {"mode": "full"},
    }
    return {
        "id": obj_id,
        "type": "lens",
        "attributes": {
            "title": title,
            "visualizationType": "lnsXY",
            "state": {
                "datasourceStates": datasource,
                "query": {"language": "kuery", "query": ""},
                "filters": [],
                "visualization": visualization,
            },
        },
        "references": [
            {"type": "index-pattern", "id": "__DATA_VIEW_ID__", "name": ref_name()}
        ],
    }


def metric_object(obj_id, title, metric):
    datasource = {
        "formBased": {
            "layers": {
                "layer1": {
                    "layerId": "layer1",
                    "layerType": "data",
                    "columns": {"metric": metric},
                    "columnOrder": ["metric"],
                    "incompleteColumns": {},
                    "indexPatternId": "__DATA_VIEW_ID__",
                }
            }
        }
    }
    return {
        "id": obj_id,
        "type": "lens",
        "attributes": {
            "title": title,
            "visualizationType": "lnsMetric",
            "state": {
                "datasourceStates": datasource,
                "query": {"language": "kuery", "query": ""},
                "filters": [],
                "visualization": {
                    "layerId": "layer1",
                    "metricAccessor": "metric",
                    "colorMode": "None",
                    "palette": {"name": "default", "type": "palette"},
                    "showBar": False,
                    "truncateLegend": False,
                },
            },
        },
        "references": [
            {"type": "index-pattern", "id": "__DATA_VIEW_ID__", "name": ref_name()}
        ],
    }


def dashboard_object(viz_ids):
    layout = [
        (AVG_SALARY_ID, 0, 0, 24, 15),
        (HEADCOUNT_ID, 24, 0, 24, 15),
        (TOTAL_ID, 0, 15, 12, 10),
        (HIRES_TREND_ID, 12, 15, 36, 10),
    ]
    panels = []
    references = []
    for index, (viz_id, x, y, w, h) in enumerate(layout, start=1):
        panel_ref = f"panel_{index}"
        panels.append(
            {
                "type": "lens",
                "version": "9.2.0",
                "gridData": {"x": x, "y": y, "w": w, "h": h, "i": panel_ref},
                "panelIndex": panel_ref,
                "embeddableConfig": {"enhancements": {}},
                "panelRefName": panel_ref,
            }
        )
        references.append({"type": "lens", "id": viz_id, "name": panel_ref})

    return {
        "id": DASHBOARD_ID,
        "type": "dashboard",
        "attributes": {
            "title": "Employee Overview",
            "description": "Headcount, salaries and hiring trend for the employees index.",
            "panelsJSON": json.dumps(panels),
            "optionsJSON": json.dumps(
                {"useMargins": True, "syncColors": False, "hidePanelTitles": False}
            ),
            "timeRestore": True,
            "timeFrom": "2018-01-01T00:00:00.000Z",
            "timeTo": "2026-12-31T23:59:59.999Z",
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": json.dumps(
                    {"query": {"language": "kuery", "query": ""}, "filter": []}
                )
            },
            "version": 1,
        },
        "references": references,
    }


def build_objects(data_view_id):
    objects = [
        xy_object(
            AVG_SALARY_ID,
            "Average Salary by Department",
            terms_column("department", "department"),
            metric_column("Average of salary", "salary", "average"),
        ),
        xy_object(
            HEADCOUNT_ID,
            "Headcount by City",
            terms_column("city", "city"),
            count_column("Employees"),
        ),
        metric_object(TOTAL_ID, "Total Employees", count_column("Total employees")),
        xy_object(
            HIRES_TREND_ID,
            "Hires Over Time",
            date_histogram_column(),
            count_column("New hires"),
            series_type="line",
        ),
        dashboard_object([AVG_SALARY_ID, HEADCOUNT_ID, TOTAL_ID, HIRES_TREND_ID]),
    ]
    serialized = json.dumps(objects).replace("__DATA_VIEW_ID__", data_view_id)
    return json.loads(serialized)


def import_objects(objects):
    for obj in objects:
        obj.setdefault("coreMigrationVersion", "9.2.0")
        if obj.get("type") == "lens":
            obj["typeMigrationVersion"] = "8.9.0"
        elif obj.get("type") == "dashboard":
            obj["typeMigrationVersion"] = "7.17.3"

    ndjson = "\n".join(json.dumps(obj) for obj in objects) + "\n"
    files = {"file": ("employees_kibana_objects.ndjson", ndjson, "application/ndjson")}
    resp = requests.post(
        f"{KIBANA_URL}/api/saved_objects/_import?overwrite=true",
        headers=HEADERS,
        files=files,
        timeout=180,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"import -> {resp.status_code}: {resp.text[:800]}")
    result = resp.json()

    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "employees_kibana_objects.ndjson"), "w", encoding="utf-8") as handle:
        handle.write(ndjson)

    if result.get("errors"):
        for err in result.get("errors", []):
            print(f"  import error: {err}")
    return result


def main():
    if not wait_for_kibana():
        raise SystemExit(1)

    data_view_id = ensure_data_view()
    objects = build_objects(data_view_id)
    result = import_objects(objects)

    print(f"Import success={result.get('success')} objects={len(objects)}")
    print("Dashboard: Employee Overview")
    print(f"Open: {KIBANA_URL}/app/dashboards#/view/{DASHBOARD_ID}")
    print("Set the time picker to 'Last 10 years' if the charts look empty.")


if __name__ == "__main__":
    main()

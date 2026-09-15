"""Validate paired VM logs using recorded wall-clock windows, not host telemetry."""

from datetime import datetime
from pathlib import Path
import re


PROTOCOL = "cpu_fixed_v1"
MARGIN_SECONDS = 5.0


def read_metadata(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    meta = {}
    for key, value in re.findall(r"^([a-z_]+):[ \t]*(.*)$", text, re.MULTILINE):
        if key in meta:
            raise ValueError(f"{path.name}: duplicate metadata field {key}")
        meta[key] = value.strip()
    return meta, text


def require(meta: dict, key: str, expected: str) -> None:
    if meta.get(key) != str(expected):
        raise ValueError(f"expected {key}={expected}, found {meta.get(key)!r}")


def timestamp(meta: dict, key: str) -> datetime:
    try:
        value = datetime.fromisoformat(meta[key])
    except (KeyError, ValueError) as exc:
        raise ValueError(f"missing/invalid timestamp: {key}") from exc
    if value.utcoffset() is None:
        raise ValueError(f"timestamp must include a timezone: {key}")
    return value


def window(meta: dict) -> tuple[datetime, datetime]:
    start, end = timestamp(meta, "started_at"), timestamp(meta, "finished_at")
    if end <= start:
        raise ValueError("finished_at must follow started_at")
    return start, end


def validate_log_pairs(raw_dir: Path, rows: list[dict], contention_dir: Path,
                       formal: bool = False) -> list[dict]:
    """Require paired identity, successful completion and at least 5s load margins.

    New logs also require warm-up coverage and synchronized-clock status. This
    does not measure clock offset or prove constant physical CPU utilization.
    Legacy smoke logs can be checked retrospectively, but cannot pass formal mode.
    """
    if not contention_dir.is_dir():
        raise ValueError(f"contention log directory does not exist: {contention_dir}")
    for directory in (raw_dir, contention_dir):
        unfinished = sorted(p.name for p in directory.glob("*.tmp"))
        if unfinished:
            raise ValueError(f"unfinished logs in {directory}: {', '.join(unfinished)}")

    studies, protocols, benchmark_settings = set(), set(), set()
    benchmarks = []
    for row in rows:
        path = raw_dir / str(row["file"])
        try:
            meta, _ = read_metadata(path)
            load, run = int(row["pressure_percent"]), int(row["run"])
            require(meta, "configured_neighbor_load_percent", str(load))
            require(meta, "run_number", str(run))
            require(meta, "hostname", "benchmark-vm")
            if not meta.get("study_name"):
                raise ValueError("missing study_name")
            if formal:
                require(meta, "study_name", "formal_v1")
                require(meta, "collection_protocol", PROTOCOL)
                for key, expected in [("benchmark_duration_seconds", "30"),
                                      ("benchmark_threads", "1"), ("warmup_seconds", "5")]:
                    require(meta, key, expected)
            start, end = window(meta)
            warmup_start = start
            if meta.get("collection_protocol"):
                require(meta, "collection_protocol", PROTOCOL)
                require(meta, "clock_synchronized", "yes")
                require(meta, "exit_status", "0")
                warmup_start = timestamp(meta, "warmup_started_at")
                warmup_end = timestamp(meta, "warmup_finished_at")
                if not warmup_start <= warmup_end <= start:
                    raise ValueError("warm-up timestamps are out of order")
                warmup_duration = float(meta["warmup_seconds"])
                if (warmup_end - warmup_start).total_seconds() + 0.05 < warmup_duration:
                    raise ValueError("warm-up finished too early")
                if (end - start).total_seconds() + 0.05 < float(row["total_time_s"]):
                    raise ValueError("benchmark timestamps do not cover reported duration")
            duration = float(meta["benchmark_duration_seconds"])
            if abs(float(row["total_time_s"]) - duration) > 1.0:
                raise ValueError("measured duration differs from configured duration by over 1s")
            settings = tuple(meta[k] for k in ("kernel", "sysbench_version", "benchmark_duration_seconds",
                                               "benchmark_threads", "warmup_seconds"))
            benchmark_settings.add(settings)
            studies.add(meta["study_name"])
            protocols.add(meta.get("collection_protocol", "legacy"))
            benchmarks.append((row, meta, warmup_start, start, end))
        except (KeyError, ValueError) as exc:
            raise ValueError(f"{path.name}: {exc}") from exc
    if len(studies) != 1 or len(protocols) != 1 or len(benchmark_settings) != 1:
        raise ValueError("mixed studies, collection protocols or benchmark settings")
    study, protocol = next(iter(studies)), next(iter(protocols))

    loads, load_settings = {}, set()
    for path in sorted(contention_dir.glob("*.txt")):
        try:
            meta, text = read_metadata(path)
            load, run = int(meta["configured_load_percent"]), int(meta["run_number"])
            if load not in (25, 50, 75, 100) or run < 1:
                raise ValueError("invalid load/run number")
            if path.name != f"contention_{load}_run_{run}.txt":
                raise ValueError("filename disagrees with load/run metadata")
            require(meta, "study_name", study)
            require(meta, "hostname", "contention-vm")
            if meta.get("collection_protocol", "legacy") != protocol:
                raise ValueError("benchmark/contention collection protocols differ")
            start, end = window(meta)
            if not re.search(r"failed:\s*0\s*$", text, re.MULTILINE):
                raise ValueError("stress-ng did not report zero failures")
            if not re.search(r"metrics untrustworthy:\s*0\s*$", text, re.MULTILINE):
                raise ValueError("stress-ng metrics were not confirmed trustworthy")
            if "successful run completed" not in text:
                raise ValueError("stress-ng success marker missing")
            if protocol == PROTOCOL:
                require(meta, "clock_synchronized", "yes")
                require(meta, "exit_status", "0")
                require(meta, "cpu_method", "int64")
                workers = int(meta["cpu_workers"])
                if workers < 1 or not re.search(rf"passed:\s*{workers}:\s*cpu \({workers}\)", text):
                    raise ValueError("successful worker count disagrees with metadata")
                duration = float(meta["contention_duration_seconds"])
                if duration <= 0 or (end - start).total_seconds() + 1.0 < duration:
                    raise ValueError("load finished before configured duration")
                if formal:
                    require(meta, "cpu_workers", "2")
                    require(meta, "contention_duration_seconds", "120")
                load_settings.add(tuple(meta[k] for k in ("kernel", "stress_ng_version", "cpu_workers",
                                                          "cpu_method", "contention_duration_seconds")))
            if (load, run) in loads:
                raise ValueError("duplicate load/run pair")
            loads[load, run] = (start, end)
        except (KeyError, ValueError) as exc:
            raise ValueError(f"{path.name}: {exc}") from exc
    if len(load_settings) > 1:
        raise ValueError("mixed contention settings or software versions")
    expected = {(int(r["pressure_percent"]), int(r["run"])) for r in rows if int(r["pressure_percent"]) > 0}
    if formal and set(loads) != expected:
        raise ValueError(f"contention trial mismatch: missing={sorted(expected-set(loads))}, extra={sorted(set(loads)-expected)}")

    checks = []
    for row, meta, warmup_start, start, end in benchmarks:
        load, run = int(row["pressure_percent"]), int(row["run"])
        result = {"file": row["file"], "load_percent": load, "run": run,
                  "load_start_margin_s": "NA", "load_end_margin_s": "NA"}
        if load == 0:
            if any(a < end and warmup_start < b for a, b in loads.values()):
                raise ValueError(f"{row['file']}: baseline overlaps a recorded load window")
            result["status"] = "no_recorded_load_overlap"
        else:
            if (load, run) not in loads:
                raise ValueError(f"{row['file']}: missing matching contention log")
            a, b = loads[load, run]
            lead, tail = (warmup_start-a).total_seconds(), (b-end).total_seconds()
            if lead < MARGIN_SECONDS or tail < MARGIN_SECONDS:
                raise ValueError(f"{row['file']}: insufficient load coverage; start margin={lead:.3f}s, end margin={tail:.3f}s; each must be >= {MARGIN_SECONDS:g}s")
            if any(key != (load, run) and x < end and warmup_start < y
                   for key, (x, y) in loads.items()):
                raise ValueError(f"{row['file']}: overlaps another contention trial")
            result.update(status="covered", load_start_margin_s=lead, load_end_margin_s=tail)
        checks.append(result)
    return checks

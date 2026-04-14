from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from collections import deque
from datetime import datetime
from html import escape
from logging.handlers import RotatingFileHandler
from pathlib import Path
from xml.etree import ElementTree as ET

from flask import Flask, request

from calculator import calculate

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "app.log"
TEST_RUNS_DIR = BASE_DIR / "test_runs"
DEFAULT_WORKERS = max(1, min(4, os.cpu_count() or 1))
DEFAULT_DIST = "loadgroup"
RESULT_STATUSES = {"PASSED", "FAILED", "ERROR", "SKIPPED", "XFAIL", "XPASS"}

XDIST_RESULT_PATTERN = re.compile(
    r"^\[(?P<worker>gw\d+)\]\s+\[\s*(?P<progress>\d+)%\]\s+"
    r"(?P<status>PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\s+"
    r"(?P<nodeid>\S+)\s*$"
)
SINGLE_RESULT_PATTERN = re.compile(
    r"^(?P<nodeid>\S+)\s+"
    r"(?P<status>PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\s+"
    r"\[\s*(?P<progress>\d+)%\]\s*$"
)


def configure_logging() -> None:
    log_path = str(LOG_FILE.resolve())
    has_app_handler = any(
        isinstance(handler, RotatingFileHandler)
        and getattr(handler, "baseFilename", None) == log_path
        for handler in app.logger.handlers
    )

    if not has_app_handler:
        handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=5)
        handler.setLevel(logging.INFO)
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        app.logger.addHandler(handler)

    app.logger.setLevel(logging.INFO)
    app.logger.propagate = False


configure_logging()


def normalize_workers(requested_workers: int | None) -> int:
    available_cpus = max(1, os.cpu_count() or 1)
    if requested_workers is None:
        return DEFAULT_WORKERS
    return max(1, min(requested_workers, available_cpus))


def normalize_dist(requested_dist: str | None) -> str:
    allowed = {"load", "loadgroup", "worksteal"}
    if requested_dist in allowed:
        return requested_dist
    return DEFAULT_DIST


def infer_operation(nodeid: str) -> str:
    test_name = nodeid.split("::")[-1].lower()
    if test_name.startswith("test_add") or "-add-" in test_name or "_add_" in test_name:
        return "add"
    if (
        test_name.startswith("test_subtract")
        or "-subtract-" in test_name
        or "_subtract_" in test_name
    ):
        return "subtract"
    if (
        test_name.startswith("test_multiply")
        or "-multiply-" in test_name
        or "_multiply_" in test_name
    ):
        return "multiply"
    if (
        test_name.startswith("test_divide")
        or "-divide-" in test_name
        or "_divide_" in test_name
    ):
        return "divide"
    return "misc"


def parse_result_line(line: str) -> dict[str, str] | None:
    for pattern in (XDIST_RESULT_PATTERN, SINGLE_RESULT_PATTERN):
        match = pattern.match(line)
        if match:
            return {
                "nodeid": match.group("nodeid"),
                "status": match.group("status"),
                "progress": match.group("progress"),
                "worker": match.groupdict().get("worker", "main"),
            }
    return None


def junit_candidate_nodeids(classname: str, test_name: str) -> list[str]:
    candidates = []
    dotted_parts = classname.split(".") if classname else []

    if dotted_parts:
        module_path = "/".join(dotted_parts) + ".py"
        candidates.append(f"{module_path}::{test_name}")

        if len(dotted_parts) > 1:
            module_path = "/".join(dotted_parts[:-1]) + ".py"
            candidates.append(f"{module_path}::{dotted_parts[-1]}::{test_name}")

    candidates.append(test_name)
    return candidates


def resolve_nodeid(
    classname: str,
    test_name: str,
    worker_by_nodeid: dict[str, str],
) -> str:
    for candidate in junit_candidate_nodeids(classname, test_name):
        if candidate in worker_by_nodeid:
            return candidate

    suffix = f"::{test_name}"
    suffix_matches = [nodeid for nodeid in worker_by_nodeid if nodeid.endswith(suffix)]
    if len(suffix_matches) == 1:
        return suffix_matches[0]

    return junit_candidate_nodeids(classname, test_name)[0]


def build_pytest_command(workers: int, dist: str, junit_path: Path) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-vv",
        "--color=no",
        f"--junit-xml={junit_path}",
    ]

    if workers > 1:
        command.extend(["-n", str(workers), f"--dist={dist}"])

    return command


def parse_junit_report(
    junit_path: Path,
    streamed_results: list[dict[str, str]],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    worker_by_nodeid = {
        result["nodeid"]: result["worker"]
        for result in streamed_results
        if result["status"] in RESULT_STATUSES
    }

    if not junit_path.exists():
        return fallback_summary(streamed_results), fallback_records(streamed_results)

    root = ET.fromstring(junit_path.read_text(encoding="utf-8"))
    testsuite = root.find("testsuite") if root.tag == "testsuites" else root

    if testsuite is None:
        return fallback_summary(streamed_results), fallback_records(streamed_results)

    total = int(testsuite.attrib.get("tests", "0"))
    failures = int(testsuite.attrib.get("failures", "0"))
    errors = int(testsuite.attrib.get("errors", "0"))
    skipped = int(testsuite.attrib.get("skipped", "0"))
    passed = max(total - failures - errors - skipped, 0)

    records: list[dict[str, object]] = []
    for testcase in testsuite.findall(".//testcase"):
        test_name = testcase.attrib.get("name", "")
        classname = testcase.attrib.get("classname", "")
        nodeid = resolve_nodeid(classname, test_name, worker_by_nodeid)

        status = "PASSED"
        details = ""
        for tag_name, mapped_status in (
            ("failure", "FAILED"),
            ("error", "ERROR"),
            ("skipped", "SKIPPED"),
        ):
            node = testcase.find(tag_name)
            if node is not None:
                status = mapped_status
                details = (node.attrib.get("message") or node.text or "").strip()
                details = " ".join(details.split())
                break

        record = {
            "test": nodeid,
            "name": test_name,
            "classname": classname,
            "operation": infer_operation(nodeid),
            "status": status,
            "worker": worker_by_nodeid.get(nodeid, "main"),
            "duration_seconds": float(testcase.attrib.get("time", "0") or 0.0),
        }
        if details:
            record["details"] = details
        records.append(record)

    summary = {
        "total": total,
        "passed": passed,
        "failed": failures + errors,
        "skipped": skipped,
        "duration_seconds": float(testsuite.attrib.get("time", "0") or 0.0),
    }
    return summary, records


def fallback_summary(streamed_results: list[dict[str, str]]) -> dict[str, object]:
    passed = sum(1 for result in streamed_results if result["status"] == "PASSED")
    failed = sum(1 for result in streamed_results if result["status"] in {"FAILED", "ERROR"})
    skipped = sum(1 for result in streamed_results if result["status"] == "SKIPPED")
    total = passed + failed + skipped
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "duration_seconds": 0.0,
    }


def fallback_records(streamed_results: list[dict[str, str]]) -> list[dict[str, object]]:
    return [
        {
            "test": result["nodeid"],
            "name": result["nodeid"].split("::")[-1],
            "classname": result["nodeid"].split("::")[0].removesuffix(".py"),
            "operation": infer_operation(result["nodeid"]),
            "status": result["status"],
            "worker": result["worker"],
            "duration_seconds": 0.0,
        }
        for result in streamed_results
    ]


def write_test_case_log(run_id: str, jsonl_path: Path, records: list[dict[str, object]]) -> None:
    with jsonl_path.open("w", encoding="utf-8") as case_log:
        for record in records:
            payload = json.dumps(record, sort_keys=True)
            case_log.write(f"{payload}\n")
            app.logger.info("TEST_CASE[%s]: %s", run_id, payload)


def run_test_suite(workers: int, dist: str) -> dict[str, object]:
    TEST_RUNS_DIR.mkdir(exist_ok=True)

    run_id = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S-%f")
    raw_output_path = TEST_RUNS_DIR / f"pytest-{run_id}.log"
    junit_path = TEST_RUNS_DIR / f"pytest-{run_id}.xml"
    test_case_path = TEST_RUNS_DIR / f"pytest-{run_id}.jsonl"

    command = build_pytest_command(workers=workers, dist=dist, junit_path=junit_path)
    app.logger.info(
        "Starting pytest execution for run %s with workers=%s dist=%s command=%s",
        run_id,
        workers,
        dist,
        " ".join(command),
    )

    process = subprocess.Popen(
        command,
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )

    streamed_results: list[dict[str, str]] = []
    last_output_lines: deque[str] = deque(maxlen=20)

    with raw_output_path.open("w", encoding="utf-8") as raw_output:
        if process.stdout is not None:
            for raw_line in process.stdout:
                raw_output.write(raw_line)
                raw_output.flush()

                line = raw_line.rstrip()
                last_output_lines.append(line)
                app.logger.info("PYTEST_OUTPUT[%s]: %s", run_id, line)

                parsed = parse_result_line(line)
                if parsed is not None:
                    streamed_results.append(parsed)

    return_code = process.wait()
    summary, records = parse_junit_report(junit_path, streamed_results)
    write_test_case_log(run_id, test_case_path, records)

    summary.update(
        {
            "run_id": run_id,
            "workers": workers,
            "dist": dist,
            "returncode": return_code,
            "status": "SUCCESS" if return_code == 0 else "FAILED",
            "raw_output_log": str(raw_output_path),
            "test_case_log": str(test_case_path),
            "junit_xml": str(junit_path),
        }
    )

    app.logger.info("TEST_SUMMARY[%s]: %s", run_id, json.dumps(summary, sort_keys=True))

    if return_code != 0 and last_output_lines:
        app.logger.error(
            "PYTEST_TAIL[%s]: %s",
            run_id,
            " | ".join(last_output_lines),
        )

    return summary


@app.route("/")
def index():
    return (
        "<h1>Hello the pytest + Flask Application</h1>"
        "<form method='post' action='/calculator'>"
        "<input name='value_1' type='number' placeholder='First number' required>"
        "<input name='value_2' type='number' placeholder='Second number' required>"
        "<select name='operation'>"
        "<option value='add'>Add</option>"
        "<option value='subtract'>Subtract</option>"
        "<option value='multiply'>Multiply</option>"
        "<option value='divide'>Divide</option>"
        "</select>"
        "<button type='submit'>Calculate</button>"
        "</form>"
        "<form method='get' action='/testall'>"
        f"<input name='workers' type='number' min='1' max='{max(1, os.cpu_count() or 1)}' value='{DEFAULT_WORKERS}'>"
        "<input name='dist' type='hidden' value='loadgroup'>"
        "<button type='submit'>Run Tests in Parallel</button>"
        "</form>"
    )


@app.route("/testall")
def test_all():
    workers = normalize_workers(request.args.get("workers", type=int))
    dist = normalize_dist(request.args.get("dist"))
    summary = run_test_suite(workers=workers, dist=dist)

    status_line = "SUCCESS" if summary["returncode"] == 0 else "FAILED"
    icon = "PASS" if summary["returncode"] == 0 else "FAIL"

    return (
        "<pre>"
        f"{icon}: {escape(status_line)}\n"
        f"Run ID: {escape(str(summary['run_id']))}\n"
        f"Workers: {escape(str(summary['workers']))}\n"
        f"Distribution: {escape(str(summary['dist']))}\n"
        f"Total: {escape(str(summary['total']))}\n"
        f"Passed: {escape(str(summary['passed']))}\n"
        f"Failed: {escape(str(summary['failed']))}\n"
        f"Skipped: {escape(str(summary['skipped']))}\n"
        f"Duration (s): {escape(str(summary['duration_seconds']))}\n"
        f"Raw output log: {escape(str(summary['raw_output_log']))}\n"
        f"Per-test log: {escape(str(summary['test_case_log']))}\n"
        f"JUnit XML: {escape(str(summary['junit_xml']))}"
        "</pre>"
    )


@app.route("/calculator", methods=["POST"])
def calculator():
    try:
        value_1 = float(request.form.get("value_1"))
        value_2 = float(request.form.get("value_2"))
        operation = request.form.get("operation")

        result = calculate(value_1, value_2, operation)
        app.logger.info(
            "Calculation requested: %s %s %s",
            value_1,
            operation,
            value_2,
        )
        return (
            f"<h3>Result: {result}</h3>"
            "<a href='/'>Go Back</a>"
        )

    except ValueError as exc:
        app.logger.error("Calculation error: %s", str(exc))
        return (
            f"<h3 style='color:red;'>Error: {escape(str(exc))}</h3>"
            "<a href='/'>Go Back</a>"
        )


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)

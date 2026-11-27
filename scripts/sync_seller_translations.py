#!/usr/bin/env python3
"""Resume a complete export → translate → review → cleanup → import cycle from a trusted workstation.
Uses the existing SSH alias and signed-in Codex CLI; credentials stay on the workstation.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--server",
        required=True,
        help="SSH alias already configured on this workstation",
    )
    p.add_argument(
        "--work-dir",
        type=Path,
        required=True,
        help="Persistent directory for resumable drafts and review",
    )
    p.add_argument("--question-comments", action="store_true", help="Перевести заново описания со служебной пометкой о знаке вопроса")
    a = p.parse_args()
    if a.server.startswith("-"):
        p.error("Invalid SSH target")
    a.work_dir.mkdir(parents=True, exist_ok=True)
    run_log = a.work_dir / "sync-history.jsonl"

    def record(event):
        with run_log.open("a", encoding="utf-8") as log:
            print(json.dumps({"event": event, "at": datetime.now(timezone.utc).isoformat(),
                              "question_comments": a.question_comments}), file=log)

    record("started")
    remote = "/opt/avtopodborimport"
    output = subprocess.check_output(
        [
            "ssh",
            a.server,
            "sudo -u postgres python3 " + remote + "/export_translation_work.py" + (" --question-comments" if a.question_comments else ""),
        ]
    )
    data = json.loads(output)
    (a.work_dir / "catalog-pending.json").write_text(
        json.dumps(data["terms"], ensure_ascii=False, indent=2) + "\n"
    )
    source = a.work_dir / "source.jsonl"
    drafts = a.work_dir / "drafts.jsonl"
    reviewed = a.work_dir / "reviewed.jsonl"
    source.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in data["descriptions"])
    )
    if not data["descriptions"]:
        record("completed")
        print("Новых описаний для перевода нет.")
        print("Catalog terms needing editorial mapping:", len(data["terms"]))
        return
    scripts = Path(__file__).resolve().parent
    for name, args in [
        ("batch_translate_with_codex.py", [source, drafts] + (["--exact-sources"] if a.question_comments else [])),
        ("review_codex_translations.py", [drafts, reviewed]),
        ("clean_reviewed_chinese.py", [reviewed]),
    ]:
        subprocess.run(
            [sys.executable, str(scripts / name), *[str(x) for x in args]], check=True
        )
    # Work directories are resumable. Only publish rows selected for this run.
    selected = {row["text"] for row in data["descriptions"]}
    if selected:
        from import_reviewed_seller_translations import prepare, read_complete_jsonl

        current = [r for r in read_complete_jsonl(reviewed) if r["text"] in selected]
        missing = selected - {r["text"] for r in current}
        if a.question_comments and missing:
            raise RuntimeError(f"Отсутствуют проверенные переводы: {len(missing)}")
        manual = []
        prepare(current, manual)
        (a.work_dir / "manual-review.jsonl").write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in manual), encoding="utf-8"
        )
        payload = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in current)
        subprocess.run(
            ["ssh", a.server, "sudo -u postgres python3 " + remote + "/import_reviewed_seller_translations.py - --apply"],
            input=payload, text=True, check=True,
        )
    record("completed")
    print("Catalog terms needing editorial mapping:", len(data["terms"]))


if __name__ == "__main__":
    main()

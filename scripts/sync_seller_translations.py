#!/usr/bin/env python3
"""Resume a complete export → translate → review → cleanup → import cycle from a trusted workstation.
Uses the existing SSH alias and signed-in Codex CLI; credentials stay on the workstation.
"""

import argparse
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
    a = p.parse_args()
    if a.server.startswith("-"):
        p.error("Invalid SSH target")
    a.work_dir.mkdir(parents=True, exist_ok=True)
    remote = "/opt/avtopodborimport"
    output = subprocess.check_output(
        [
            "ssh",
            a.server,
            "sudo -u postgres python3 " + remote + "/export_translation_work.py",
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
    scripts = Path(__file__).resolve().parent
    for name, args in [
        ("batch_translate_with_codex.py", [source, drafts]),
        ("review_codex_translations.py", [drafts, reviewed]),
        ("clean_reviewed_chinese.py", [reviewed]),
    ]:
        subprocess.run(
            [sys.executable, str(scripts / name), *[str(x) for x in args]], check=True
        )
    target = "/tmp/avto-reviewed-import.jsonl"
    subprocess.run(["scp", str(reviewed), a.server + ":" + target], check=True)
    subprocess.run(
        [
            "ssh",
            a.server,
            "sudo -u postgres python3 "
            + remote
            + "/import_reviewed_seller_translations.py "
            + target
            + " --apply",
        ],
        check=True,
    )
    print("Catalog terms needing editorial mapping:", len(data["terms"]))


if __name__ == "__main__":
    main()

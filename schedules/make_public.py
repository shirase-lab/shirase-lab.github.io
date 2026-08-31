#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""live 平文（フル {meta, events}）から“公開用”平文を作る（アプリ／公開Webが取得する live.json 用）。

- events から内部項目を除去: uchiwa_demand / sns_priority / fan_service_culture / verified /
  notes / lineup_note。
  ※ lineup_note は「出演・日程」等の公開情報に内部分析（うちわ需要・施策・裏取り補足・status遷移）が
    文中で混在しており、文単位クリーンでは漏れが残るため、公開ファイルからは丸ごと落とす。
    公演の出演者は公開 `lineup`（配列）、日程は `dates` があるので情報は足りる。
    ※将来 lineup_note を公開に残したい場合は、ジョブ側で lineup_note を“公開情報のみ”に統一してから
      ここの DROP から外す（daily_update.md 参照）。
- meta は公開に必要な report_week / generated_at のみ残す（purpose/notes/label_schema は内部）。
- 出力は暗号化前の平文。crypt.sh enc で live.json（公開・アプリ取得先）に暗号化する。

  python schedules/make_public.py <full_plain.json> [out_plain.json]   # out省略=stdout
"""
import json
import sys
from pathlib import Path

DROP = {"uchiwa_demand", "sns_priority", "fan_service_culture", "verified", "notes", "lineup_note"}
META_KEEP = {"report_week", "generated_at"}


def make_public(doc):
    meta = {k: v for k, v in (doc.get("meta") or {}).items() if k in META_KEEP}
    events = [{k: v for k, v in e.items() if k not in DROP} for e in doc.get("events", [])]
    return {"meta": meta, "events": events}


def main():
    if len(sys.argv) < 2:
        print("usage: make_public.py <full_plain.json> [out]", file=sys.stderr)
        sys.exit(2)
    doc = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    pub = make_public(doc)
    out = json.dumps(pub, ensure_ascii=False, indent=2) + "\n"
    if len(sys.argv) > 2 and sys.argv[2] != "-":
        Path(sys.argv[2]).write_text(out, encoding="utf-8")
        print(f"public plaintext -> {sys.argv[2]} ({len(pub['events'])} events)", file=sys.stderr)
    else:
        sys.stdout.write(out)


if __name__ == "__main__":
    main()

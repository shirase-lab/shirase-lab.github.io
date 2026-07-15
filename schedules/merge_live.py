#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""schedules/live.json の決定的 upsert マージャ（平文どうしを合成）。

- base（前回の live 平文・full doc {meta, events}）に、incoming（今回の調査で
  見つけた/更新するイベント。full doc でも events 配列でも可）を **id で upsert**。
  id が一致したらそのイベントを incoming で**丸ごと差し替え**（＝古い absent 等の
  取り残しを防ぐ。ジョブは触れたイベントを必ず完全な形で出す前提）。id が無ければ追加。
- base だけにあり incoming に無いイベントは**そのまま残す**（未再取得＝削除ではない）。
- meta.generated_at = 実行日、meta.report_week = 実行日を含む月〜日（ISO週）に更新。

使い方:
  python schedules/merge_live.py --base prev.json --incoming found.json --out merged.json [--today YYYY-MM-DD]
"""
import argparse
import datetime
import json
import sys


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def events_of(doc):
    return doc if isinstance(doc, list) else doc.get("events", [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="前回 live 平文（full doc）")
    ap.add_argument("--incoming", required=True, help="今回の found（doc または events 配列）")
    ap.add_argument("--out", required=True)
    ap.add_argument("--today", help="YYYY-MM-DD（既定=実行日）")
    a = ap.parse_args()

    base = load(a.base)
    if not isinstance(base, dict) or "events" not in base or "meta" not in base:
        print("ERROR: base は {meta, events} の full document である必要があります", file=sys.stderr)
        sys.exit(2)

    incoming = events_of(load(a.incoming))
    today = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    sunday = monday + datetime.timedelta(days=6)

    order = [e["id"] for e in base["events"] if "id" in e]
    by_id = {e["id"]: e for e in base["events"] if "id" in e}

    added, updated, skipped = [], [], 0
    for ev in incoming:
        eid = ev.get("id")
        if not eid:
            skipped += 1
            continue
        if eid in by_id:
            updated.append(eid)
        else:
            order.append(eid)
            added.append(eid)
        by_id[eid] = ev  # replace/insert（丸ごと差し替え）

    base["events"] = [by_id[i] for i in order]
    base["meta"]["generated_at"] = today.isoformat()
    base["meta"]["report_week"] = "{0}/{1}".format(monday.isoformat(), sunday.isoformat())

    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(base, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("merged: base={0} +added={1} ~updated={2} skipped_no_id={3} -> total={4} | week={5}".format(
        len(order) - len(added), len(added), len(updated), skipped,
        len(base["events"]), base["meta"]["report_week"]))


if __name__ == "__main__":
    main()

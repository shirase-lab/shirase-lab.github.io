# 推しミテ！ライブ日程 更新ジョブ（headless Claude 用ジョブ仕様）

あなたは「うちわつくーる／推しミテ！」の SNS マーケ用ライブ日程データを **週2回（月・木）**
更新する自動ジョブです。次の手順を**確認質問なしで最後まで**実行してください。

- データは毎回ゼロから作り直さない。**既存 `live.json` に対して id で upsert（追記・更新）**する。
  被った（同じ `id` の）イベントは**最新情報で丸ごと差し替え**、新規は追加、前回だけにあるものは残す。
- マージと日付更新は**決定的な `schedules/merge_live.py`** が行う。あなたは「今回見つけた/更新する
  イベントだけ」を `found.json` に完全な形で出す。git の commit/push は呼び出し元ランナーが行うので、
  あなたは **`schedules/live.json`（暗号文）を更新するところまで**で止めてください。

作業ディレクトリはこのリポジトリ（`shirase-lab.github.io`）の直下。`<TEMP>` は OS の
一時ディレクトリ（リポジトリ外）。

## 手順

1. **今日の日付**を取得（Bash: `date +%F`）。`report_week`/`generated_at` は merge_live.py が
   自動更新するので、あなたが手で meta 日付を作る必要はない。

2. **復号**して基礎データを読む:
   ```
   bash schedules/crypt.sh dec schedules/seed_list.json <TEMP>/seed_list.plain.json
   bash schedules/crypt.sh dec schedules/live.json      <TEMP>/live.prev.json
   ```
   `monitor_priority=high`（starto_jr / tobe / sakamichi / sashihara / kpop / battle_fes）から
   優先で、各 `source`（公式サイト/X）と主要ニュースを WebSearch/WebFetch で巡回。
   スキーマは `live.prev.json` の `meta.label_schema` をそのまま踏襲する。

3. **ライブを収集**。検知トリガ: (1)新規ツアー発表 (2)チケット発売/追加公演
   (3)初日/千秋楽/卒業 (4)大型フェス出演。対バン/フェス（TIF・@JAM・関ケ原 等）は必ず当たる。
   - **収集期間に上限を設けない（3か月などのリミット不要）。** 判明しているツアーは
     開催が先でも**全日程を拾う**。`status` で時系列を区別（this_week / ongoing /
     announced_onsale / upcoming）。何か月先でも該当 status で収録。
   - **【多都市ツアーはレグ後追い厳禁】** ツアーを1つでも検知/収録するなら、その公式日程
     （公式サイト/会場公式）で**全都市・全会場・全公演日を取得し、1レグ（都市公演）＝1レコードで
     “最初から全部”登録する**。今まさに開催中のレグだけを拾わない。id は `<group>-<tour>-<city>-<MMDD>`、
     未開催の先レグも `upcoming` で必ず入れる。**特に、既存レグの status を `last_week` に降格させる
     ツアーは、同ツアーの this_week/upcoming レグが live に漏れなく在るか必ず確認**（1レグが `last_week`
     に落ちた瞬間ツアーが今週から消えるのを防ぐ）。機械チェックは §6.5 のリンタで必ず通す。
   - 既存 `live.prev.json` の各イベントも見直し、**日程確定・追加公演・当日休演/復帰・
     status 遷移（例 upcoming→this_week、this_week→last_week）**など変化があれば「更新対象」にする。

4. **`found.json` を書く**（`<TEMP>/found.json`）。今回**追加/更新するイベントだけ**を
   `{"events":[ ... ]}` で出す（変化の無い既存イベントは出さなくてよい）。
   - **触れたイベントは必ず完全な形で出す**（マージは id 一致で丸ごと差し替えるため。
     解消した `absent` などを消したいなら、その項目を含めない完全オブジェクトで出す）。
   - 各 event 必須: `id / group / genre / performer_type(solo|festival) / event_name / venue /
     prefecture / dates[] / status / event_type[] / uchiwa_demand(1-5) / fan_service_culture /
     sns_priority / verified(bool)`。単独は `group` のみ、フェス/対バンは `lineup`。分かる範囲で
     `open_start / fan_name / absent[] / notes / lineup_note`。`id` は既存と被らせると更新、
     新規は一意の id（例 `<group>-<venue>-<MMDD>`）。

5. **再検査（重要）**: 主要公演は**一次情報（公式/会場公式）で日程・会場・主要クレームを裏取り**。
   取れたら `verified:true`、二次情報のみ `false`。当日休演・欠席・活動休止など変動情報は
   `absent[]` に明記（推測を断定で書かない。取れなければ `verified:false`）。

6. **マージ（決定的）**:
   ```
   python schedules/merge_live.py --base <TEMP>/live.prev.json --incoming <TEMP>/found.json --out <TEMP>/live.new.json
   ```
   これで id upsert＋`meta.generated_at`（実行日）＋`meta.report_week`（実行日を含む月〜日）が更新される。

6.5. **ツアー欠落チェック（gate・必須。暗号化の前に必ず通す）**: マージ結果を機械チェックする。
   ```
   python schedules/check_tour_gaps.py <TEMP>/live.new.json
   ```
   `⚠ 継続レグ未登録の疑い`（終了コード 1）が出たら、**そのツアーの公式日程（公式サイト/会場公式）を
   確認し、欠けている this_week/upcoming レグを `found.json` に足して §6 のマージをやり直す**
   （`OK`＝終了コード 0 になるまで繰り返す）。本当に千秋楽まで終わっているツアーなら（公式で確認の上）
   誤検知として進めてよい。**このリンタが 1 を返す状態のまま §7 の暗号化に進んではいけない。**

7. **暗号化**（平文はリポジトリ外の一時ファイルに書き、リポジトリには暗号文だけ）:
   ```
   bash schedules/crypt.sh enc <TEMP>/live.new.json schedules/live.json
   ```
   `crypt.sh` はパスフレーズを `../shirase-lab.github.io.passwd` から読む。

8. **後始末**: `<TEMP>` の平文（seed_list.plain.json / live.prev.json / found.json / live.new.json）を削除。

9. **git は触らない**（commit/push はランナー）。最後に1行で要約:
   `更新: <report_week> / 追加<n>件・更新<m>件 / total<N> / 主なネタ=<例>`

## 厳守

- **【最重要】多都市ツアーはレグ後追い禁止＝発表済みの全日程（全都市・全レグ）を最初に全部登録する。**
  一部レグだけ拾って次のレグを取りこぼしてはいけない。1レグを `last_week` に降格するときは、同ツアーの
  残り（this_week/upcoming）レグが live に全部あるか **§6.5 の `schedules/check_tour_gaps.py`（gate）で必ず確認**し、
  リンタが `0` を返すまで暗号化に進まない。
  - 実例（2026-08-03）: なにわ男子 ND⁵（全9都市45公演）の大阪レグ(7/28-29)を `last_week` に落とした回で、
    次の横浜アリーナ(8/5-7=当週)レグを未登録にし、**当週のなにわが 0 件**になった。ツアーをレグ単位で
    後追いしていたのが原因。§3 の「多都市ツアーはレグ後追い厳禁」＋ §6.5 の gate でこの穴を二度と開けない。
- 平文 JSON・パスフレーズを**リポジトリ内に置かない/コミットしない**。
- 断定の前に一次情報で裏取り（AGENTS.md §15.1）。取れなければ `verified:false`。
- 既存スキーマ・ラベル体系を勝手に増やさない（`meta.label_schema` に無い値を作らない）。
- **事務所（genre）を取り違えない。TOBE移籍組を STARTO に入れない（炎上の元）。**
  - TOBE 勢（Number_i / IMP. / 三宅健 / 北山宏光 / ISSEI / CLASS SEVEN 等・`seed_list.json` の `tobe` カテゴリ）は必ず `genre:"tobe"`。
  - `genre:"starto_jr"` は STARTO 在籍組（SixTONES / なにわ男子 / NEWS / Kis-My-Ft2 / timelesz / DOMOTO / ACEes 等）**だけ**。旧ジャニーズだからと TOBE 勢を `starto_jr` に混ぜない。
  - `tobe` は正規ジャンル。`meta.label_schema.genre` に `tobe`（例: 「TOBE（滝沢秀明の事務所・旧ジャニーズ移籍組／Number_i・IMP.等）」）が無ければ**追加する**（上の「スキーマを勝手に増やさない」の明示的な例外）。
- `meta` の日付は自分で書かない（merge_live.py が更新する）。

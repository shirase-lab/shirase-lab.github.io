"""推しミテ！ライブ日程 更新ジョブを Claude Agent SDK で実行する（Run-LiveSchedule.ps1 から呼ぶ）。

以前は `claude -p`（Claude Code＝Max の利用枠）で動かしていた。Agent SDK＋API キーにすると、
Max プランに付く月次 API クレジット（Claude Console の Promotional credits）から引かれる。

- 認証はこのジョブ専用の環境変数 OSHIMITE_ANTHROPIC_API_KEY のみ。SDK の子プロセスにだけ
  ANTHROPIC_API_KEY として渡す（ユーザー環境変数を ANTHROPIC_API_KEY にすると、対話の Claude Code や
  ほかの claude -p まで API キーで動いてしまうため）。無ければ何もせず終了コード 4。
- ジョブ仕様は daily_update.md をそのまま渡す。git の commit/push は呼び出し元の PowerShell が行う。
- 1 回の実行の上限金額は --max-budget-usd（既定 5 ドル）。超えたら途中で止まる。

使い方:
  python schedules/run_live_agent.py [--model MODEL] [--max-budget-usd 5]
終了コード: 0=成功 / 1=エージェントがエラーで終了 / 4=API キー未設定
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeSDKError,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

HERE = Path(__file__).resolve().parent          # <repo>/schedules
REPO = HERE.parent                              # <repo>（oshimite.jp）
# リポジトリ外の内部フル暗号ファイル（D:/ShiraseLab/oshimite.jp.live.internal.json）と
# crypt.sh のパスフレーズ（<repo の親>/shirase-lab.github.io.passwd）を読み書きするため。
EXTRA_DIRS = [REPO.parent, Path("D:/ShiraseLab")]


async def run(model: str | None, max_budget_usd: float) -> int:
    api_key = os.environ.get("OSHIMITE_ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        print("ERROR: OSHIMITE_ANTHROPIC_API_KEY が未設定です（月次 API クレジットの組織のキーを設定してください）。", flush=True)
        return 4

    env = {"ANTHROPIC_API_KEY": api_key}
    # ワークスペースに属さない（組織の）キーのときは、使うワークスペースの ID が要る。
    workspace = os.environ.get("OSHIMITE_ANTHROPIC_WORKSPACE_ID", "").strip()
    if workspace:
        env["ANTHROPIC_CUSTOM_HEADERS"] = f"anthropic-workspace-id: {workspace}"

    spec = (HERE / "daily_update.md").read_text(encoding="utf-8")
    options = ClaudeAgentOptions(
        # claude -p と同じ振る舞い（Claude Code の既定プロンプト・設定ファイル）にそろえる。
        system_prompt={"type": "preset", "preset": "claude_code"},
        setting_sources=["user", "project", "local"],
        cwd=str(REPO),
        add_dirs=[str(d) for d in EXTRA_DIRS],
        # headless は権限プロンプトに答えられないので、以前と同じくバイパス（Bash/Web/Edit が要る）。
        permission_mode="bypassPermissions",
        model=model,
        max_budget_usd=max_budget_usd,
        env=env,
        stderr=lambda line: print(f"[stderr] {line}", flush=True),
    )

    exit_code = 0
    try:
        async for message in query(prompt=spec, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock) and block.text.strip():
                        print(block.text, flush=True)
                    elif isinstance(block, ToolUseBlock):
                        print(f"[tool] {block.name}", flush=True)
            elif isinstance(message, ResultMessage):
                cost = message.total_cost_usd
                print(
                    f"[result] subtype={message.subtype} turns={message.num_turns} "
                    f"cost_usd={cost if cost is not None else '?'} "
                    f"models={','.join((message.model_usage or {}).keys()) or '?'}",
                    flush=True,
                )
                if message.is_error:
                    exit_code = 1
    except ClaudeSDKError as e:
        print(f"ERROR: {e}", flush=True)
        return 1
    return exit_code


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", default=None, help="モデル（未指定＝既定）")
    parser.add_argument("--max-budget-usd", type=float, default=5.0, help="1 回の上限金額（USD）")
    args = parser.parse_args()
    sys.exit(asyncio.run(run(args.model, args.max_budget_usd)))


if __name__ == "__main__":
    main()

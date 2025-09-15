#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "claude-code-sdk==0.0.22",
#   "rich",
# ]
# requires-python = ">=3.11"
# [tool.uv]
# exclude-newer = "2025-09-15T12:41:05Z"
# ///

"""
タスク管理エージェント

効果的なタスク管理機能を提供するClaude Code SDKエージェント。
CSVファイルベースの永続化とインタラクティブなタスク操作をサポート。

Usage:
    ./agents/task_manager/main.py
    ./agents/task_manager/main.py --demo
"""

import argparse
import asyncio
import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from claude_code_sdk import (
    ClaudeSDKClient,
    ClaudeCodeOptions,
    tool,
    create_sdk_mcp_server,
    AssistantMessage,
    TextBlock,
    ResultMessage,
    SystemMessage,
    ToolUseBlock,
)
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt


# Rich コンソール
console = Console()

# タスクファイルのパス
TASK_FILE = Path(__file__).parent / "tasks.csv"

# タスクの状態定義
TASK_STATUSES = ["未着手", "進行中", "レビュー中", "完了"]
TASK_PRIORITIES = ["高", "中", "低"]

# CSVヘッダー
CSV_HEADERS = ["id", "name", "priority", "status", "created_at", "updated_at"]

# アイコン定義
STATUS_ICONS = {"未着手": "⭕", "進行中": "🔄", "レビュー中": "👀", "完了": "✅"}

PRIORITY_ICONS = {"高": "🔥", "中": "📋", "低": "📝"}

# システムプロンプト定義（グローバル）
SYSTEM_PROMPT = """あなたは高度なタスク管理専門エージェントです。タスク管理の効率化と組織化を支援することが唯一の使命です。

<role>
あなたはタスク管理のエキスパートとして、以下の機能のみを提供します：
- タスクの追加、更新、削除、完了処理
- タスクステータスの管理（未着手、進行中、レビュー中、完了）
- タスク優先度の設定と管理（高、中、低）
- タスクリストの表示、フィルタリング、整理
- タスクの進捗追跡と報告
</role>

<core_principles>
1. 専門性の厳守：タスク管理に関連する操作のみを実行
2. データ整合性：タスクデータの正確性と一貫性を最優先
3. 透明性：すべての操作と結果を明確に報告
4. 信頼性：不確実な場合は必ず確認を求める
</core_principles>

<boundaries>
以下のリクエストは処理できません：
- タスク管理以外の業務（コード作成、文書作成、計算、分析など）
- タスクデータ以外のファイル操作
- 外部システムへのアクセスや統合
- タスク管理の範囲を超えた助言や推論
- 個人情報や機密情報の取り扱い
</boundaries>

<tools_specification>
利用可能なツール：
- add_task: 新規タスク追加（name: 必須, priority: 高/中/低）
- list_tasks: タスク一覧表示（status_filter, priority_filter: オプション）
- update_task: タスク更新（task_identifier, status, priority）
- done_task: タスク完了（task_identifier）
- delete_task: タスク削除（task_identifier）

各ツールは明確な目的でのみ使用し、結果を必ず確認してください。
</tools_specification>

<response_format>
応答は以下の形式に従います：
1. 実行する操作の明確な説明
2. ツール実行と結果の報告
3. 次のアクションの提案（必要な場合）
4. エラーや制限事項の明確な説明
</response_format>

<uncertainty_handling>
不明確な場合の対処：
- 「私の理解では[解釈内容]ですが、正しいでしょうか？」と確認
- 複数の解釈が可能な場合は選択肢を提示
- 必要な情報が不足している場合は具体的に要求
</uncertainty_handling>

<rejection_protocol>
タスク管理以外のリクエストへの標準応答：
「申し訳ございません。私はタスク管理専門のエージェントです。[リクエスト内容]については対応できません。以下のタスク管理機能をご利用ください：
• タスクの追加・更新・削除
• タスクの一覧表示とフィルタリング
• タスクの完了処理
• 優先度やステータスの管理」
</rejection_protocol>

<error_handling>
エラー発生時は内容を明確に説明し、考えられる原因と解決策を提示します。
</error_handling>

<consistency_rules>
- タスクの状態遷移は論理的な順序に従う
- 削除されたタスクは復元不可能であることを警告
- すべての日時はISO 8601形式で記録
</consistency_rules>

<hallucination_prevention>
- 存在しないタスクについて推測しない
- 不確実な情報は「情報が不足しています」と明確に伝える
- タスクデータはCSVファイルから読み込んだ内容のみを使用
</hallucination_prevention>

重要：タスク管理機能の範囲内で最高のサービスを提供し、範囲外のリクエストは丁寧かつ明確に拒否してください。"""


def ensure_task_file():
    """タスクファイルが存在しない場合は作成する"""
    if not TASK_FILE.exists():
        with open(TASK_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)


def load_tasks() -> List[Dict[str, str]]:
    """CSVファイルからタスクを読み込む"""
    ensure_task_file()
    tasks = []
    try:
        with open(TASK_FILE, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                tasks.append(row)
    except FileNotFoundError:
        pass
    return tasks


def save_tasks(tasks: List[Dict[str, str]]):
    """タスクをCSVファイルに保存"""
    with open(TASK_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(tasks)


def get_next_task_id() -> int:
    """次のタスクIDを生成（連番）"""
    tasks = load_tasks()
    if not tasks:
        return 1

    max_id = max(int(task["id"]) for task in tasks)
    return max_id + 1


@tool(
    "add_task",
    "新しいタスクを追加します。タスク名と優先度を指定してタスクを作成できます。",
    {
        "name": str,
        "priority": str,  # "高", "中", "低" のいずれか
    },
)
async def add_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """新しいタスクを追加"""
    task_name = args["name"]
    priority = args.get("priority", "中")

    if priority not in TASK_PRIORITIES:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"❌ エラー: 優先度は {', '.join(TASK_PRIORITIES)} のいずれかを指定してください。",
                }
            ]
        }

    # 新しいタスクを作成
    now = datetime.now().isoformat()
    new_task = {
        "id": str(get_next_task_id()),
        "name": task_name,
        "priority": priority,
        "status": "未着手",
        "created_at": now,
        "updated_at": now,
    }

    # 既存タスクを読み込み、新しいタスクを追加
    tasks = load_tasks()
    tasks.append(new_task)
    save_tasks(tasks)

    return {
        "content": [
            {
                "type": "text",
                "text": f"✅ タスクを追加しました:\n📝 {task_name}\n🔥 優先度: {priority}\n📅 作成日時: {now}",
            }
        ]
    }


@tool(
    "list_tasks",
    "タスク一覧を表示します。オプションでステータス（未着手、進行中、レビュー中、完了）や優先度（高、中、低）でフィルタリング可能。フィルタを指定しない場合は全タスクを表示。",
    {
        "status_filter": str,  # オプション: "未着手", "進行中", "レビュー中", "完了" のいずれか。指定しない場合は全て表示
        "priority_filter": str,  # オプション: "高", "中", "低" のいずれか。指定しない場合は全て表示
    },
)
async def list_tasks(args: Dict[str, Any]) -> Dict[str, Any]:
    """タスク一覧を表示"""
    tasks = load_tasks()

    # フィルタリング（有効な値のみ適用）
    status_filter = args.get("status_filter")
    priority_filter = args.get("priority_filter")

    filtered_tasks = tasks
    if status_filter and status_filter in TASK_STATUSES:
        filtered_tasks = [t for t in filtered_tasks if t["status"] == status_filter]
    if priority_filter and priority_filter in TASK_PRIORITIES:
        filtered_tasks = [t for t in filtered_tasks if t["priority"] == priority_filter]

    if not filtered_tasks:
        filter_text = ""
        if status_filter or priority_filter:
            filters = []
            if status_filter:
                filters.append(f"ステータス: {status_filter}")
            if priority_filter:
                filters.append(f"優先度: {priority_filter}")
            filter_text = f" ({', '.join(filters)})"

        return {
            "content": [
                {
                    "type": "text",
                    "text": f"📋 タスクが見つかりませんでした{filter_text}",
                }
            ]
        }

    # Richテーブルでタスクリストを作成
    table = Table(title="📋 タスク一覧", show_header=True, header_style="bold blue")
    table.add_column("ID", style="dim", width=4)
    table.add_column("タスク名", style="bold", min_width=20)
    table.add_column("優先度", justify="center", width=8)
    table.add_column("ステータス", justify="center", width=10)
    table.add_column("作成日時", style="dim", width=16)

    for task in filtered_tasks:
        status_icon = STATUS_ICONS.get(task["status"], "❓")
        priority_icon = PRIORITY_ICONS.get(task["priority"], "❓")

        table.add_row(
            task["id"],
            task["name"],
            f"{priority_icon} {task['priority']}",
            f"{status_icon} {task['status']}",
            task["created_at"][:16],
        )

    # テーブルを文字列として取得
    from io import StringIO

    string_io = StringIO()
    temp_console = Console(file=string_io, width=100, legacy_windows=False)
    temp_console.print(table)
    table_output = string_io.getvalue()

    return {"content": [{"type": "text", "text": table_output}]}


@tool(
    "update_task",
    "タスクのステータスまたは優先度を更新します。タスクIDまたはタスク名で指定できます。",
    {
        "task_identifier": str,  # タスクIDまたはタスク名
        "status": str,  # オプション: 新しいステータス
        "priority": str,  # オプション: 新しい優先度
    },
)
async def update_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """タスクの更新"""
    task_identifier = args["task_identifier"]
    new_status = args.get("status")
    new_priority = args.get("priority")

    if not new_status and not new_priority:
        return {
            "content": [
                {
                    "type": "text",
                    "text": "❌ エラー: ステータスまたは優先度のいずれかを指定してください。",
                }
            ]
        }

    # バリデーション
    if new_status and new_status not in TASK_STATUSES:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"❌ エラー: ステータスは {', '.join(TASK_STATUSES)} のいずれかを指定してください。",
                }
            ]
        }

    if new_priority and new_priority not in TASK_PRIORITIES:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"❌ エラー: 優先度は {', '.join(TASK_PRIORITIES)} のいずれかを指定してください。",
                }
            ]
        }

    # タスクを検索
    tasks = load_tasks()
    task_to_update = None
    for task in tasks:
        if task["id"] == task_identifier or task["name"] == task_identifier:
            task_to_update = task
            break

    if not task_to_update:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"❌ エラー: タスクが見つかりません: {task_identifier}",
                }
            ]
        }

    # タスク更新
    updates = []
    if new_status:
        task_to_update["status"] = new_status
        updates.append(f"ステータス: {new_status}")
    if new_priority:
        task_to_update["priority"] = new_priority
        updates.append(f"優先度: {new_priority}")

    task_to_update["updated_at"] = datetime.now().isoformat()
    save_tasks(tasks)

    return {
        "content": [
            {
                "type": "text",
                "text": f"✅ タスクを更新しました:\n📝 {task_to_update['name']}\n🔄 {', '.join(updates)}",
            }
        ]
    }


@tool(
    "done_task",
    "タスクを完了状態にします。よく使う操作のショートカットです。",
    {
        "task_identifier": str  # タスクIDまたはタスク名
    },
)
async def done_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """タスクを完了にする（ショートカット）"""
    return await update_task(
        {"task_identifier": args["task_identifier"], "status": "完了"}
    )


@tool(
    "delete_task",
    "タスクを削除します。タスクIDまたはタスク名で指定できます。",
    {
        "task_identifier": str  # タスクIDまたはタスク名
    },
)
async def delete_task(args: Dict[str, Any]) -> Dict[str, Any]:
    """タスクを削除"""
    task_identifier = args["task_identifier"]

    # タスクを検索
    tasks = load_tasks()
    task_to_delete = None
    for i, task in enumerate(tasks):
        if task["id"] == task_identifier or task["name"] == task_identifier:
            task_to_delete = tasks.pop(i)
            break

    if not task_to_delete:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"❌ エラー: タスクが見つかりません: {task_identifier}",
                }
            ]
        }

    save_tasks(tasks)

    return {
        "content": [
            {
                "type": "text",
                "text": f"🗑️ タスクを削除しました: {task_to_delete['name']}",
            }
        ]
    }


def display_message(msg):
    """メッセージをRichで美しく表示"""
    if isinstance(msg, AssistantMessage):
        for block in msg.content:
            if isinstance(block, TextBlock):
                # Claudeの応答を美しいパネルで表示
                claude_panel = Panel(
                    Text(block.text, style="white"),
                    title="🤖 Claude",
                    title_align="left",
                    border_style="blue",
                    padding=(0, 1),
                )
                console.print(claude_panel)
            elif isinstance(block, ToolUseBlock):
                # ツール使用を情報パネルで表示
                tool_info = f"[bold cyan]ツール:[/bold cyan] {block.name}"
                if block.input:
                    # 入力パラメータを整形
                    input_str = ", ".join([f"{k}={v}" for k, v in block.input.items()])
                    tool_info += f"\n[dim]入力: {input_str}[/dim]"

                tool_panel = Panel(
                    tool_info,
                    title="🔧 ツール実行",
                    title_align="left",
                    border_style="green",
                    padding=(0, 1),
                )
                console.print(tool_panel)
    elif isinstance(msg, SystemMessage):
        # システムメッセージは無視
        pass
    elif isinstance(msg, ResultMessage):
        # 結果は Claude の応答で既に表示されているため、コストのみ表示
        if msg.total_cost_usd:
            console.print(f"💰 [dim]コスト: ${msg.total_cost_usd:.6f}[/dim]")


async def process_claude_response(client, prompt_text: str):
    """Claudeの応答をSpinnerと共に処理"""
    await client.query(prompt_text)

    # Spinnerを表示しながら応答を待つ
    with console.status(
        "[bold green]🤖 Claude が考えています...", spinner="dots"
    ) as status:
        async for message in client.receive_response():
            # メッセージを受信したらSpinnerを一時停止して表示
            status.stop()
            display_message(message)
            # 次のメッセージがまだある場合はSpinnerを再開
            if isinstance(message, (AssistantMessage, SystemMessage)):
                status.start()


async def demo_mode():
    """デモモードでの自動実行"""
    welcome_panel = Panel(
        "🎬 デモモードを開始します...",
        title="タスク管理エージェント デモ",
        title_align="center",
        border_style="magenta",
        padding=(1, 2),
    )
    console.print(welcome_panel)

    # MCP サーバーを作成
    task_server = create_sdk_mcp_server(
        name="task-manager",
        version="1.0.0",
        tools=[add_task, list_tasks, update_task, done_task, delete_task],
    )

    # Claude Code オプション設定
    options = ClaudeCodeOptions(
        mcp_servers={"task_manager": task_server},
        allowed_tools=[
            "mcp__task_manager__add_task",
            "mcp__task_manager__list_tasks",
            "mcp__task_manager__update_task",
            "mcp__task_manager__done_task",
            "mcp__task_manager__delete_task",
        ],
        permission_mode="acceptEdits",
        max_turns=5,
        system_prompt=SYSTEM_PROMPT,
    )

    demo_prompts = [
        "タスク一覧を表示してください",
        "「新しいプロジェクトの企画書作成」というタスクを高優先度で追加してください",
        "「API ドキュメントの更新」というタスクを中優先度で追加してください",
        "「新しいプロジェクトの企画書作成」タスクを完了にしてください",
        "残っているタスクの一覧を表示してください",
    ]

    for i, prompt in enumerate(demo_prompts, 1):
        console.print()  # 改行

        # プロンプトを美しく表示
        prompt_panel = Panel(
            Text(prompt, style="bold yellow"),
            title=f"🤖 ステップ {i}/{len(demo_prompts)}",
            title_align="left",
            border_style="yellow",
            padding=(0, 1),
        )
        console.print(prompt_panel)

        # ClaudeSDKClient を使用してSpinnerと共に処理
        async with ClaudeSDKClient(options=options) as client:
            await process_claude_response(client, prompt)

        # 少し待機
        await asyncio.sleep(1)

    # 完了メッセージ
    completion_panel = Panel(
        "🎉 デモが完了しました！",
        title="完了",
        title_align="center",
        border_style="green",
        padding=(1, 2),
    )
    console.print(completion_panel)


async def interactive_mode():
    """インタラクティブモード"""
    welcome_text = """📋 タスク管理エージェントへようこそ！

自然な日本語でタスクを管理できます。
例: 「新機能の設計書作成タスクを追加」「進行中のタスクを表示」

[dim]終了方法: 'quit', 'exit', 'q' または Ctrl-D[/dim]"""

    welcome_panel = Panel(
        welcome_text,
        title="🚀 タスク管理エージェント",
        title_align="center",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(welcome_panel)

    # MCP サーバーを作成
    task_server = create_sdk_mcp_server(
        name="task-manager",
        version="1.0.0",
        tools=[add_task, list_tasks, update_task, done_task, delete_task],
    )

    # Claude Code オプション設定
    options = ClaudeCodeOptions(
        mcp_servers={"task_manager": task_server},
        allowed_tools=[
            "mcp__task_manager__add_task",
            "mcp__task_manager__list_tasks",
            "mcp__task_manager__update_task",
            "mcp__task_manager__done_task",
            "mcp__task_manager__delete_task",
        ],
        permission_mode="acceptEdits",
        system_prompt=SYSTEM_PROMPT,
    )

    while True:
        try:
            console.print()
            user_input = Prompt.ask("[bold cyan]💬 あなた[/bold cyan]").strip()

            if user_input.lower() in ["quit", "exit", "q"]:
                goodbye_panel = Panel(
                    "👋 ありがとうございました！",
                    title="さようなら",
                    title_align="center",
                    border_style="green",
                    padding=(0, 2),
                )
                console.print(goodbye_panel)
                break

            if not user_input:
                continue

            # ClaudeSDKClient を使用してSpinnerと共に処理
            async with ClaudeSDKClient(options=options) as client:
                await process_claude_response(client, user_input)

        except KeyboardInterrupt:
            goodbye_panel = Panel(
                "👋 ありがとうございました！",
                title="中断されました",
                title_align="center",
                border_style="yellow",
                padding=(0, 2),
            )
            console.print(goodbye_panel)
            break
        except EOFError:
            goodbye_panel = Panel(
                "👋 ありがとうございました！",
                title="EOF",
                title_align="center",
                border_style="green",
                padding=(0, 2),
            )
            console.print(goodbye_panel)
            break
        except Exception as e:
            error_panel = Panel(
                f"❌ エラーが発生しました: {e}",
                title="エラー",
                title_align="left",
                border_style="red",
                padding=(0, 1),
            )
            console.print(error_panel)


async def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="タスク管理エージェント - 効果的なタスク管理をサポート"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="デモモードで実行（決まったプロンプトを自動実行）",
    )

    args = parser.parse_args()

    try:
        if args.demo:
            await demo_mode()
        else:
            await interactive_mode()
    except Exception as e:
        error_panel = Panel(
            f"❌ 予期しないエラーが発生しました: {e}",
            title="致命的エラー",
            title_align="left",
            border_style="red",
            padding=(0, 1),
        )
        console.print(error_panel, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

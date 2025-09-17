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

import asyncio
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
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

console = Console()

DB_FILE = Path(__file__).parent / "tasks.db"

TASK_STATUSES = ["未着手", "進行中", "レビュー中", "完了"]
TASK_PRIORITIES = ["高", "中", "低"]

STATUS_ICONS = {"未着手": "⭕", "進行中": "🔄", "レビュー中": "👀", "完了": "✅"}
PRIORITY_ICONS = {"高": "🔥", "中": "📋", "低": "📝"}

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
- change_task_status: タスクのステータス変更（task_id, status）

注意：更新・削除などの操作はID指定のみに対応します。名前は重複の可能性があるため使用しません。

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


def get_db_connection() -> sqlite3.Connection:
    """データベース接続を取得"""
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn


def ensure_database():
    """データベースとテーブルが存在しない場合は作成する"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def load_tasks(
    status_filter: Optional[str] = None, priority_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """データベースからタスクを読み込む"""
    ensure_database()
    conn = get_db_connection()
    cursor = conn.cursor()

    conditions = []
    params = []

    if status_filter and status_filter in TASK_STATUSES:
        conditions.append("status = ?")
        params.append(status_filter)

    if priority_filter and priority_filter in TASK_PRIORITIES:
        conditions.append("priority = ?")
        params.append(priority_filter)

    query = "SELECT * FROM tasks"
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY id"

    cursor.execute(query, params)
    tasks = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return tasks


def get_task_by_id(task_id: int | str) -> Optional[Dict[str, Any]]:
    """IDでタスクを取得"""
    try:
        tid = int(task_id)
    except (TypeError, ValueError):
        return None

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (tid,))
    task = cursor.fetchone()
    conn.close()
    return dict(task) if task else None


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

    ensure_database()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """INSERT INTO tasks (name, priority, status)
           VALUES (?, ?, ?)""",
        (task_name, priority, "未着手"),
    )
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "content": [
            {
                "type": "text",
                "text": (
                    "✅ タスクを追加しました:\n"
                    f"#️⃣ ID: {task_id}\n"
                    f"📝 {task_name}\n"
                    f"🔥 優先度: {priority}"
                ),
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
    status_filter = args.get("status_filter")
    priority_filter = args.get("priority_filter")

    filtered_tasks = load_tasks(status_filter, priority_filter)

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

    table = Table(title="📋 タスク一覧", show_header=True, header_style="bold blue")
    table.add_column("ID", style="dim", width=4)
    table.add_column("タスク名", style="bold", min_width=20)
    table.add_column("優先度", justify="center", width=8)
    table.add_column("ステータス", justify="center", width=10)

    for task in filtered_tasks:
        status_icon = STATUS_ICONS.get(task["status"], "❓")
        priority_icon = PRIORITY_ICONS.get(task["priority"], "❓")

        table.add_row(
            str(task["id"]),
            task["name"],
            f"{priority_icon} {task['priority']}",
            f"{status_icon} {task['status']}",
        )

    from io import StringIO

    string_io = StringIO()
    temp_console = Console(file=string_io, width=100, legacy_windows=False)
    temp_console.print(table)
    table_output = string_io.getvalue()

    return {"content": [{"type": "text", "text": table_output}]}


@tool(
    "change_task_status",
    "タスクのステータスを変更します。IDで指定してください。",
    {
        "task_id": int,  # タスクID（数値）
        "status": str,  # 新しいステータス（未着手/進行中/レビュー中/完了）
    },
)
async def change_task_status(args: Dict[str, Any]) -> Dict[str, Any]:
    """タスクのステータスを変更"""
    task_id = args.get("task_id")
    new_status = args.get("status")

    if task_id is None:
        return {
            "content": [
                {"type": "text", "text": "❌ エラー: タスクIDを指定してください。"}
            ]
        }

    # task_id は数値のみサポート
    try:
        int(task_id)
    except (TypeError, ValueError):
        return {
            "content": [
                {
                    "type": "text",
                    "text": "❌ エラー: タスクIDは数値で指定してください。",
                }
            ]
        }

    if not new_status:
        return {
            "content": [
                {
                    "type": "text",
                    "text": "❌ エラー: 新しいステータスを指定してください。",
                }
            ]
        }

    if new_status not in TASK_STATUSES:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"❌ エラー: ステータスは {', '.join(TASK_STATUSES)} のいずれかを指定してください。",
                }
            ]
        }

    task_to_update = get_task_by_id(task_id)

    if not task_to_update:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"❌ エラー: タスクが見つかりません: ID={task_id}",
                }
            ]
        }

    old_status = task_to_update.get("status")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE tasks SET status = ? WHERE id = ?",
        (new_status, task_to_update["id"]),
    )
    conn.commit()
    conn.close()

    status_change = (
        f"{old_status} → {new_status}"
        if old_status and old_status != new_status
        else new_status
    )

    return {
        "content": [
            {
                "type": "text",
                "text": (
                    "✅ タスクのステータスを更新しました:\n"
                    f"#️⃣ ID: {task_to_update['id']}\n"
                    f"📝 {task_to_update['name']}\n"
                    f"🔄 {status_change}"
                ),
            }
        ]
    }


def display_message(msg):
    """メッセージをRichで美しく表示"""
    if isinstance(msg, AssistantMessage):
        for block in msg.content:
            if isinstance(block, TextBlock):
                claude_panel = Panel(
                    Text(block.text, style="white"),
                    title="🤖 Claude",
                    title_align="left",
                    border_style="blue",
                    padding=(0, 1),
                )
                console.print(claude_panel)
            elif isinstance(block, ToolUseBlock):
                tool_info = f"[bold cyan]ツール:[/bold cyan] {block.name}"
                if block.input:
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
        pass
    elif isinstance(msg, ResultMessage):
        if msg.total_cost_usd:
            console.print(f"💰 [dim]コスト: ${msg.total_cost_usd:.6f}[/dim]")


async def process_claude_response(client, prompt_text: str):
    """Claudeの応答をSpinnerと共に処理"""
    await client.query(prompt_text)

    with console.status(
        "[bold green]🤖 Claude が考えています...", spinner="dots"
    ) as status:
        async for message in client.receive_response():
            status.stop()
            display_message(message)
            if isinstance(message, (AssistantMessage, SystemMessage)):
                status.start()


async def interactive_mode():
    """インタラクティブモード"""
    welcome_text = """📋 タスク管理エージェントへようこそ！

自然な日本語でタスクを管理できます。
例: 「新機能の設計書作成タスクを追加」「進行中のタスクを表示」

[dim]終了方法: 'quit', 'exit', 'q'[/dim]"""

    welcome_panel = Panel(
        welcome_text,
        title="🚀 タスク管理エージェント",
        title_align="center",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(welcome_panel)

    task_server = create_sdk_mcp_server(
        name="task-manager",
        version="1.0.0",
        tools=[add_task, list_tasks, change_task_status],
    )

    options = ClaudeCodeOptions(
        mcp_servers={"task_manager": task_server},
        allowed_tools=[
            "mcp__task_manager__add_task",
            "mcp__task_manager__list_tasks",
            "mcp__task_manager__change_task_status",
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
    try:
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

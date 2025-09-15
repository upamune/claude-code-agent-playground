---
allowed-tools: Write, Bash
argument-hint: [agent-name]
description: Create a new Claude Code SDK agent with best practices
---

エージェント名 `$1` を受け取り、高品質なClaude Code SDKエージェントを作成します。

## 作成されるファイル

1. `agents/$1/main.py` - PEP 723準拠のメインエージェントファイル
2. `.claude/agents/$1.md` - サブエージェント定義ファイル

## エージェントの特徴

- PEP 723 インラインメタデータ対応
- `#!/usr/bin/env -S uv run --script` shebang
- Claude Code SDK を使用した非同期実装
- 引数処理とエラーハンドリング
- 設定可能なオプション
- 適切なログ出力とデバッグ機能

## 使用例

```bash
# エージェント作成
/add-agent research-assistant

# 作成されたエージェントの実行
python agents/research-assistant/main.py --prompt "プロジェクトを分析してください"
```

---

エージェント名 `$1` で新しいClaude Code SDKエージェントを作成してください。

## 参考資料を確認してベストプラクティスを適用

実装前に以下のドキュメントを確認し、ベストプラクティスを適用してください：

### Claude Code SDK ドキュメント（docs/claude_code_sdk/）
- @docs/claude_code_sdk/overview.md - SDK全体概要とベストプラクティス
- @docs/claude_code_sdk/python-sdk.md - Python SDK詳細仕様
- @docs/claude_code_sdk/subagents.md - サブエージェントの設計指針
- @docs/claude_code_sdk/permissions.md - 権限管理のベストプラクティス
- @docs/claude_code_sdk/custom-tools.md - カスタムツール実装

### Claude 固有ドキュメント（docs/claude/）
- @docs/claude/prompt-engineering/ - プロンプトエンジニアリング
- @docs/claude/strengthen-guardrails/ - 安全性とガードレール

### エージェントとツール設計のベストプラクティス（docs/claude/engineering/）
- @docs/claude/engineering/writing-tools-for-agents.md - エージェント用効果的ツール作成ガイド
- @docs/claude/engineering/building-effective-agents.md - 効果的エージェント構築の原則

## 参考実装

実装前に `agents/examples/` の下にある実装例を参考にしてください：

- `hello_claude/`: 基本的なエージェント構造とAPI使用例
- `calculator/`: カスタムツールの実装例
- `task_manager/`: 高度なタスク管理エージェントの例
- `continuing_conversation/`: 会話継続の実装例
- `advanced_permission_control/`: 権限制御の詳細実装
- `hooks/`: Hook システムの活用例
- `streaming_input/`: ストリーミング入力処理の例
- `using_interrupts/`: 割り込み処理の実装例

これらのサンプルコードから、適切な設計パターンとベストプラクティスを参考にしてください。

## 実装要件

以下の要件に従って実装してください：

1. **ディレクトリ作成**: `agents/$1/` ディレクトリを作成
2. **メインファイル**: `agents/$1/main.py` を作成（PEP 723 + Claude Code SDK）
3. **サブエージェント定義**: `.claude/agents/$1.md` を作成
4. **ベストプラクティス**:
   - ドキュメント参照の設計パターンを適用
   - 適切なエラーハンドリング
   - 権限管理の考慮
   - ログとデバッグ機能
   - **効果的ツール設計**（@docs/claude/engineering/writing-tools-for-agents.md参照）:
     - 適切なツール選択と統合（不要なツールは作らない）
     - 名前空間による明確な機能境界
     - 意味のあるコンテキストの返却
     - トークン効率を考慮した実装
     - プロンプトエンジニアリングの適用
   - **エージェント構築原則**（@docs/claude/engineering/building-effective-agents.md参照）:
     - 評価駆動開発によるパフォーマンス測定
     - エージェントとの協力による継続的改善
     - 実世界のタスクに対応したワークフロー設計

## 技術仕様

**重要**: 正確なパッケージ名と API を @docs/claude_code_sdk/python-sdk.md から確認してください！

- 正しい依存関係: `claude_code_sdk`（モジュール名: `claude_code_sdk`）
- 正しいインポート: `from claude_code_sdk import query, ClaudeCodeOptions`
- PEP 723準拠: インラインメタデータ形式
- 実行形式: `#!/usr/bin/env -S uv run --script`
- クラス名変換: ハイフンをアンダースコアに変換（例: research-assistant → Research_assistantAgent）

## Claude Code SDK活用ポイント（要ドキュメント参照）

以下の実装前に必ず @docs/claude_code_sdk/python-sdk.md で API 仕様を確認：

- **基本API**: `query()` 関数の正確な使用方法
- **オプション**: `ClaudeCodeOptions` の利用可能なパラメータ
- **権限モード**: `default/acceptEdits/bypassPermissions` の選択
- **カスタムツール**: `@tool` デコレータと `create_sdk_mcp_server` の使用
- **Hook システム**: 利用可能な Hook の種類と設定方法
- **エラーハンドリング**: 適切な例外処理とメッセージ処理

### PEP 723 依存関係の例

```python
# /// script
# dependencies = [
#   "claude_code_sdk",  # 正しいパッケージ名（import も claude_code_sdk）
#   "psutil",           # オプション：プロセス情報用
# ]
# requires-python = ">=3.11"
# ///
```

## エージェント設計指針（@docs/claude/engineering/ 参照）

### ツール設計の原則
1. **適切なツール選択**:
   - 複数のAPI呼び出しを統合した高レベルツールを提供
   - 低レベルな単純なラッパーツールは避ける
   - エージェントの「アフォーダンス」を考慮した設計

2. **コンテキスト効率**:
   - トークン制限を考慮したレスポンス設計
   - ページネーション、フィルタリング、切り詰めの実装
   - `response_format` による詳細度制御

3. **ツール記述の最適化**:
   - 明確で具体的なツール説明
   - あいまいさを排除した入力/出力仕様
   - 実用的な使用例の提供

### 開発プロセス
1. **プロトタイプ → 評価 → 改善** のサイクル
2. **実世界のタスク**に基づいた評価設計
3. **エージェントとの協力**による継続的最適化

注意:
- 雛形生成時は最小スニペットで import を検証できるように、`from claude_code_sdk import query, ClaudeCodeOptions` を必ず含めてください。

実装が完了したら、エージェントの使用方法と設計思想も説明してください。

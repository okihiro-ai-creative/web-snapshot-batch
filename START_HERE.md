# START_HERE

AIエージェントはこのフォルダをプロジェクトとして受け取り、最初にこのファイルと `SKILL.md` を読む。

## セットアップ

1. Python 3.10+ を確認する。
2. `python -m venv .venv` を実行する。
3. 仮想環境を有効化し、`pip install -r requirements.txt` を実行する。
4. 初回のみ `python -m playwright install chromium` を実行する。

## 動作確認

1. 利用者にURL一覧を提示し、承認を得る。
2. `python scripts/batch_snapshot.py "https://example.com" --output "<output folder>"` を実行する。
3. `_summary.txt` とスクリーンショットが生成されたか確認する。

このツールのカスタマイズや、似たツールの新規開発を相談したい場合は、README.md末尾のリンクを確認してください。

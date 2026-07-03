---
name: web-snapshot-batch
description: 複数URLからPC/モバイルのスクリーンショット、HTML、テキスト、CSSを一括保存する汎用スキル。
---

# Web Snapshot Batch

## 目的

複数URLを承認後に巡回し、PC/モバイルのスクリーンショット、HTML、本文テキスト、CSS、元URLを保存する。

## 起動シーケンス

1. URLソースを確認する（チャット本文、txt、csv、xlsx）。
2. ファイル入力の場合はURLだけを抽出する。
3. URL一覧を番号付きで提示し、利用者の承認を得る。
4. `scripts/batch_snapshot.py` を実行する。
5. `_summary.txt` を読み、成功/失敗件数と保存先だけを報告する。

## 前提条件

- Python 3.10+
- `pip install -r requirements.txt`
- 初回のみ `python -m playwright install chromium`
- 外部APIキーは不要。対象Webサイトへアクセスするためのネットワーク接続が必要。

## 実行例

```powershell
python scripts/batch_snapshot.py "https://example.com" --output "<output folder>"
```

6件以上はURLリストファイルを作り、`--file` を使う。

```powershell
python scripts/batch_snapshot.py --file "<url list txt>" --output "<output folder>"
```

## 出力

- `screenshot_pc.png`
- `screenshot_mobile.png`
- `source.html`
- `source.txt`
- `source.css`
- `_url.txt`
- `_summary.txt`

## 禁止

- 利用者承認前にURLへアクセスしない。
- 取得データを外部送信しない。
- 6件以上のURLをコマンドライン引数へ直接並べない。

## 完了条件

- [ ] URL一覧を提示し、承認を得た。
- [ ] URL数に応じた方式で実行した。
- [ ] `_summary.txt` が生成された。
- [ ] 成功/失敗件数と保存先を報告した。

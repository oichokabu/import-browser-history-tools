# import-browser-history-tools
ブラウザ間で履歴ファイルをインポートする自作ツール

## TL;DR

- この手順では、MacOS（筐体:MacBook Air M3 2024、OS:Sequoia 15.0）での操作手順を示しています。WindowsOSの方は参考にならないと思います。
- この手順では、Firefox から Chrome へ 履歴をコピーする一例を記載します。任意のブラウザに読み替えてください。
- このツールは、Chromeにすでに存在する履歴テーブルに対して、Firefoxの履歴レコードを追加します。
- まず、Firefoxの履歴レコードをChromeにインポートするために、csvに起こしてから実行します。ChromeとFirefoxでは、履歴のタイムスタンプのデータ形式が異なるためです。

## 使い方- How to use

### 0. 前提

- ローカルにsqlite3をインストール済みであること。
  - `$ brew install sqlite` # brewでインストールする
  - `$ sqlite3` # インストールされたか確認する
- ローカルにvscodeをインストール済みであること。
- vscodeにsqlite3の拡張機能をインストール済みであること。

### 1. 履歴DBの確認

- 下記のPATHにFirefoxの履歴DBが格納されています。存在するか確認してください。（9flyiwxy.defaultは環境によって文字列が異なります）（以下、`places.sqlite`）
    - `'/Users/{ユーザー名}/Library/Application Support/Firefox/Profiles/9flyiwxy.default/places.sqlite'`

- 下記のPATHにChromeの履歴DBが格納されています。存在するか確認してください。（以下、`History`）
  - `'/Users/{ユーザー名}/Library/Application Support/Google/Chrome/Default/History'`

### 2. バックアップ

- 履歴DBを誤って削除・不整更新してしまった場合に備えて、Firefox・Chromeともにバックアップをとっておく。
- `places.sqlite` を 任意の場所（例：デスクトップなど）にコピーする。（※移動ではない）
- `History` を 任意の場所（例：デスクトップなど）にコピーする。（※移動ではない）

### 3. ブラウザを終了する

- Chromeブラウザを必ず終了する（バックグラウンド処理も停止する）
- Firefoxブラウザを必ず終了する（バックグラウンド処理も停止する）
- 以降、最後の確認手順までブラウザは起動してはいけない。

### 4. 事前準備（変換用のcsvファイルを抽出する）

- Firefox の履歴（`places.sqlite` ）を CSV に抽出するため、下記を実行する。

```sh
# 作業場所に移動する。この例では、作業ディレクトリを/Desktop/firefox2chrome_work/とする。
$ cd ~/Desktop/firefox2chrome_work/

# 抽出コマンド（<！>フルパスに置き換えてください。<！>XXXX.defaultは自身の環境に合わせたディレクトリ名置き換えてください。）
$ sqlite3 -header -csv \
  "~/Library/Application Support/Firefox/Profiles/XXXX.default/places.sqlite" \
  "SELECT p.url AS url, COALESCE(p.title,'') AS title, v.visit_date AS visit_date_us FROM moz_places p JOIN moz_historyvisits v ON p.id = v.place_id ORDER BY v.visit_date;" \
  > firefox_history_extraction.csv
```

- 同ディレクトリ（`Desktop/firefox2chrome_work/`）に、`firefox_history_extraction.csv`が作成されたことを目視確認する。
  - <!>履歴が多い場合は作成に時間がかかる。作成中に無理に開くと破損するので、15~30分待機する。

- 中身を確認する

```sh
$ wc -l firefox_history_extraction.csv
# header 行を除いて表示したいなら `expr $(wc -l < firefox_history_extraction.csv) - 1`
```

### 5. 事前確認（Chrome 側の現在の件数を確認）

- 現状確認のため、Chromeの`History`の履歴レコード件数を確認する。出力された数値をメモしておく。
sqlite3 "/Users/{ユーザー名}/Library/Application Support/Google/Chrome/Default/History" \
  "SELECT (SELECT COUNT(*) FROM urls) AS urls_count, (SELECT COUNT(*) FROM visits) AS visits_count;"

### 6. 実行する前に、試験実施をしておく

- 本番実行の前にdry-runでテスト実行する。dry-runにより、何件追加されるかを把握する。
- <!> `--dry-run`オプションを必ずつけること。

```sh
python3 import_firefox_history_to_chrome.py \
  --csv ~/Desktop/firefox2chrome_work/firefox_history_extraction.csv \
  --chrome-history "/Users/{ユーザー名}/Library/Application Support/Google/Chrome/Default/History" \
  --dry-run
```

- 実行結果を確認する。下記のような表示であればOK。

```sh
CSV rows parsed: 237692
[DRY-RUN] Would insert visits: 237678, duplicates skipped: 14
```

### 7. 実行する（本番）

- 下記コマンドを実行し、`places.sqlite`の履歴レコードを`History`の履歴レコードに追加する。

```sh
python3 import_firefox_history_to_chrome.py \
  --csv ~/Desktop/firefox2chrome_work/firefox_history_extraction.csv \
  --chrome-history "/Users/{ユーザー名}/Library/Application Support/Google/Chrome/Default/History"
```

- 実行結果を確認する。下記のような表示であればOK。

```sh
CSV rows parsed: 237692
Backup created: ../Chrome/History.bak.20251129015347
Inserted visits: 237624
URLs added: 76716
Duplicates skipped: 68
```

### 8. Chromeへの反映を確認する

- Chromeブラウザを起動する
- URL入力欄に、`chrome://history/`を入力する。
- 履歴ページが表示されるので、Firefoxの履歴情報が追加されたことを目視確認する

以上

# Video Compressor - Stage 2

## 概要

PythonのTCPソケットとFFmpegを使用して作成した、CLI形式の動画処理サービスです。

クライアントから動画ファイルと処理内容をサーバーへ送信し、サーバー側でFFmpegを使用して動画処理を実行します。

動画処理は別スレッドで非同期に実行され、クライアントはJob IDを使用して処理状況を定期的に確認します。処理が完了すると、加工済みファイルをサーバーからダウンロードできます。

クライアントとサーバー間の通信にはTCPを使用し、JSONデータ・メディアタイプ・ファイルデータを送受信するための独自アプリケーションプロトコル「MMP」を実装しています。

---

## 主な機能

### 動画処理

以下の動画処理に対応しています。

* 動画の圧縮
* 解像度の変更
* アスペクト比の変更
* MP3形式での音声抽出
* GIF形式のクリップ作成
* WEBM形式のクリップ作成

動画処理にはFFmpeg / ffprobeを使用しています。

---

## システム構成

```text
Client
  │
  │ TCP / MMP
  ▼
Server
  │
  ├── MMPメッセージ受信
  │
  ├── Job作成
  │
  ├── ThreadPoolExecutor
  │       │
  │       └── FFmpegによる動画処理
  │
  ├── Jobの状態管理
  │
  └── 処理済みファイルをクライアントへ返却
```

動画アップロード後、サーバーは動画処理の完了を待たずにJob IDをクライアントへ返します。

クライアントはJob IDを使用して一定間隔でサーバーへ処理状況を問い合わせます。

```text
動画アップロード
      ↓
Job作成
      ↓
status = processing
      ↓
Job IDをクライアントへ返却
      ↓
FFmpeg処理
      ↓
completed / failed
      ↓
クライアントがステータス確認
      ↓
completedの場合はファイルをダウンロード
```

---

## MMP（独自アプリケーションプロトコル）

クライアントとサーバーの通信では、TCP上に独自のMMPプロトコルを実装しています。

MMPメッセージは以下の構造です。

```text
+----------------+-------------------+----------------+
| Header (8byte) | JSON / Media Type | Payload        |
+----------------+-------------------+----------------+
```

### Header

8バイト固定長のヘッダーを使用します。

```text
+----------------+----------------------+----------------+
| JSON Size      | Media Type Size      | Payload Size   |
| 2 bytes        | 1 byte               | 5 bytes        |
+----------------+----------------------+----------------+
```

各フィールドは以下を表します。

| フィールド           |     サイズ | 内容             |
| --------------- | ------: | -------------- |
| JSON Size       | 2 bytes | JSONデータのサイズ    |
| Media Type Size |  1 byte | メディアタイプ文字列のサイズ |
| Payload Size    | 5 bytes | ファイルデータのサイズ    |

Payload Sizeは5バイトで表現するため、最大約1TBのPayloadを扱えます。

---

## MMPメッセージの種類

### JSONのみ

Jobのステータス確認やエラーレスポンスではPayloadを送信しません。

```text
Header
JSON
```

### ファイルを含むメッセージ

動画アップロードや処理済みファイルの返却では以下の形式を使用します。

```text
Header
JSON
Media Type
Payload
```

TCPでは1回の `send()` と1回の `recv()` が対応する保証がないため、ヘッダーに記録されたサイズを利用して必要なバイト数を受信するようにしています。

---

## ファイル受信

動画ファイルは1400バイト単位で受信し、サーバーの `uploads` ディレクトリへ保存します。

受信途中のファイルは一時ファイルとして保存します。

```text
UUID.temp
```

すべてのデータを正常に受信した場合のみ、

```text
UUID.mp4
```

などの正式なファイルへ変更します。

通信途中で切断された場合、一時ファイルを削除することで不完全なファイルが残らないようにしています。

---

## 非同期Job処理

動画処理には時間がかかる可能性があるため、リクエストを受信するメイン処理とFFmpeg処理を分離しています。

`ThreadPoolExecutor` を使用し、FFmpeg処理をワーカースレッドで実行します。

```python
ThreadPoolExecutor(max_workers=4)
```

同時に実行する動画処理を最大4Jobに制限しています。

これにより、動画処理中でもサーバーは新しい接続やJobのステータス確認を受け付けることができます。

---

## Job管理

各動画処理リクエストをJobとして管理します。

Jobには主に以下の情報を保持します。

```text
job_id
client_ip
operation
status
input_path
output_path
params
error
```

Job IDにはUUIDを使用しています。

Jobのステータスは主に以下の3種類です。

```text
processing
completed
failed
```

複数スレッドからJob情報へアクセスするため、JobManager内部では `threading.Lock` を使用して排他制御を行っています。

---

## 同一IPからの多重処理制限

同じIPアドレスから同時に複数の動画処理Jobを実行できないようにしています。

既に処理中のJobが存在する場合は、新しい動画処理リクエストを拒否します。

```text
JOB_ALREADY_PROCESSING
```

---

## ステータスポーリング

動画アップロード後、サーバーから以下のようなレスポンスを受け取ります。

```json
{
  "job_id": "...",
  "status": "processing"
}
```

クライアントはJob IDを保持し、一定間隔で新しいTCP接続を作成して処理状況を確認します。

```json
{
  "operation": "check_status",
  "job_id": "..."
}
```

### processing

処理中の場合はJSONのみ返します。

```json
{
  "job_id": "...",
  "status": "processing"
}
```

### completed

動画処理が完了している場合は、JSONと処理済みファイルを同じMMPメッセージで返します。

```text
JSON
Media Type
Processed File
```

### failed

動画処理に失敗した場合はエラー情報を返します。

---

## エラーハンドリング

エラー発生時は、基本的に以下の形式のJSONを返します。

```json
{
  "status": "failed",
  "error_code": "...",
  "description": "...",
  "solution": "..."
}
```

主なエラーには以下があります。

| Error Code             | 内容                   |
| ---------------------- | -------------------- |
| INVALID_REQUEST        | リクエスト形式が不正           |
| PAYLOAD_REQUIRED       | 動画ファイルが指定されていない      |
| JOB_NOT_FOUND          | Job IDが存在しない         |
| JOB_ACCESS_DENIED      | 他のIPアドレスからJobへアクセスした |
| JOB_ALREADY_PROCESSING | 同じIPでJobが既に実行中       |
| PROCESSING_FAILED      | FFmpeg処理に失敗          |
| STORAGE_LIMIT_EXCEEDED | サーバーのストレージ容量上限を超える   |

通信途中で接続が切断された場合も、不完全なファイルを削除して処理します。

---

## ストレージ容量制限

サーバー側で一時的に保存するユーザーファイルの容量を制限しています。

容量計算の対象は、

```text
uploads/
+
outputs/
```

です。

新しいPayloadを受信する前に、

```text
現在のストレージ使用量
+
受信予定のPayloadサイズ
```

を計算し、4TBを超える場合はPayloadをファイルへ保存せず、以下のエラーを返します。

```text
STORAGE_LIMIT_EXCEEDED
```

FFmpegが生成する出力ファイルの最終サイズは処理前に確定できないため、この制限はアップロード受付時点でのストレージ容量を基準としています。

---

## 一時ファイルの削除

ユーザーファイルはサーバーに永続保存せず、一時ファイルとして扱います。

処理完了後にクライアントへのファイル送信が終了すると、

```text
入力ファイル
処理済みファイル
Job情報
```

を削除します。

動画処理に失敗した場合も、クライアントがJobの失敗状態を確認した後に関連ファイルを削除します。

---

## 動画処理

### 動画圧縮

H.264を使用して動画を圧縮します。

主なFFmpeg設定：

```text
libx264
CRF 23
preset medium
```

### 解像度変更

FFmpegの `scale` フィルタを使用して指定した解像度へ変更します。

H.264エンコードとの互換性を考慮し、widthとheightには正の偶数を指定します。

### アスペクト比変更

ffprobeを使用して元動画の解像度を取得し、指定されたアスペクト比になるように中央部分をクロップします。

### 音声抽出

動画の音声ストリームをMP3形式で抽出します。

```text
libmp3lame
```

### GIF / WEBM作成

動画の開始時間と終了時間を指定して、一部分をGIFまたはWEBM形式として出力できます。

WEBMでは主に以下のコーデックを使用します。

```text
Video: VP9
Audio: Opus
```

---

## ディレクトリ構成

```text
stage2/
├── client.py
├── server.py
├── protocol.py
├── transport.py
├── ffmpeg_service.py
├── request_processor.py
├── job_manager.py
├── storage.py
├── uploads/
├── outputs/
└── downloads/
```

### 各ファイルの役割

| ファイル                   | 役割                                   |
| ---------------------- | ------------------------------------ |
| `client.py`            | CLI入力、動画アップロード、ステータスポーリング、ファイルダウンロード |
| `server.py`            | TCPサーバー、リクエスト受付、レスポンス送信              |
| `protocol.py`          | MMPヘッダー・JSON・メディアタイプのエンコード / デコード    |
| `transport.py`         | MMPメッセージの送受信                         |
| `ffmpeg_service.py`    | FFmpeg / ffprobeを使用した動画処理            |
| `request_processor.py` | Jobごとの動画処理実行                         |
| `job_manager.py`       | Jobの作成・状態管理                          |
| `storage.py`           | サーバーストレージ容量の管理                       |

---

## 使用技術

* Python 3
* TCP Socket
* FFmpeg
* ffprobe
* Threading
* ThreadPoolExecutor
* UUID
* JSON
* Python Standard Library

---

## 実行方法

### 1. FFmpegのインストール確認

```bash
ffmpeg -version
ffprobe -version
```

### 2. サーバー起動

```bash
python server.py
```

### 3. クライアント起動

別のターミナルから実行します。

```bash
python client.py
```

クライアントのCLIから処理内容と動画ファイルを指定します。

---

## Stage 2で学んだこと

このプロジェクトでは、ライブラリやWebフレームワークに通信処理を任せるのではなく、TCPソケットからアプリケーションレベルの通信処理を実装しました。

特に以下について理解を深めました。

* TCPがメッセージ境界を持たないことを考慮したデータ受信
* 独自アプリケーションプロトコルの設計
* 固定長ヘッダーを利用した可変長データの送受信
* 大容量ファイルのストリーム処理
* 一時ファイルを利用した不完全アップロード対策
* FFmpegを利用したサーバーサイド動画処理
* Jobによる非同期処理の管理
* ThreadPoolExecutorを利用した並行処理
* Lockを利用した共有データの排他制御
* ポーリングによる非同期処理結果の取得
* エラーレスポンスの設計
* サーバー側のストレージ容量管理
* 処理済みファイルのライフサイクル管理

Webフレームワークでは抽象化されることの多い通信・ファイル転送・非同期処理の仕組みを、低レイヤーから実装することで、クライアントサーバーアーキテクチャとバックエンド処理の基礎を学びました。

# Video Compressor

PythonのTCPソケットとFFmpegを使用して実装した、クライアント・サーバー型の動画処理サービスです。

Webフレームワークを使用せず、TCPソケットによるファイル転送、独自アプリケーションプロトコル、非同期Job処理、動画処理などを段階的に実装しています。

## Project Overview

このプロジェクトは2つのStageに分かれています。

```text
Stage 1
TCPによる動画ファイルアップロード
        ↓
Stage 2
独自プロトコル + FFmpegによる動画処理サービス
```

---

## Stage 1 - File Upload Server

TCPソケットを使用して、クライアントからMP4ファイルをサーバーへアップロードするCLIアプリケーションを実装しました。

### 主な機能

* TCPによるMP4ファイル転送
* CLIからアップロードファイルを指定
* ファイルサイズを利用した受信データ量の管理
* 1400バイト単位でのファイル送受信
* 不完全なアップロードの検出
* 通信切断時の一時ファイル削除
* アップロード結果のステータスレスポンス
* サーバーのストレージ容量制限
* 大容量ファイルを使用した負荷テスト

Stage 1では、TCPがメッセージ境界を持たないことを考慮し、必要なバイト数を確実に受信するファイル転送処理を実装しました。

詳細は [Stage 1 README](./Stage1/README.md) を参照してください。

---

## Stage 2 - Video Processing Server

Stage 1のファイル転送を発展させ、クライアントから動画と処理内容を送信し、サーバー側でFFmpegを使用して動画処理を実行するサービスを実装しました。

### 対応している動画処理

* 動画圧縮
* 解像度変更
* アスペクト比変更
* MP3形式での音声抽出
* GIF形式のクリップ作成
* WEBM形式のクリップ作成

### 主な機能

* TCP上の独自アプリケーションプロトコル「MMP」
* JSON・Media Type・Payloadの送受信
* 大容量ファイルのストリーム転送
* FFmpeg / ffprobeによる動画処理
* Job IDによる処理管理
* ThreadPoolExecutorによる非同期動画処理
* 最大4Jobの同時FFmpeg実行
* ステータスポーリング
* `threading.Lock` を利用したJob管理の排他制御
* 同一IPからの多重Job制限
* エラーコードを利用したエラーレスポンス
* サーバーストレージの容量制限
* 処理完了後の一時ファイル削除

詳細は [Stage 2 README](./Stage2/README.md) を参照してください。

---

## Architecture

```text
                    TCP / MMP

┌──────────────┐                  ┌────────────────────┐
│    Client    │ ───────────────▶ │       Server       │
│              │                  │                    │
│ CLI          │                  │ Request Handling   │
│ Upload       │                  │ Job Management     │
│ Polling      │                  │ ThreadPoolExecutor │
│ Download     │                  │        │           │
└──────────────┘                  │        ▼           │
                                  │     FFmpeg         │
                                  │        │           │
                                  │        ▼           │
                                  │ Processed File     │
                                  └────────────────────┘
```

Stage 2では、動画のアップロード後にサーバーがJob IDを返し、FFmpeg処理をワーカースレッドで実行します。

クライアントはJob IDを使用してサーバーへ定期的に処理状態を問い合わせ、処理完了後に生成されたファイルをダウンロードします。

---

## MMP - Custom Application Protocol

Stage 2では、TCP上に独自のMMPプロトコルを実装しています。

```text
+----------------+----------------------+----------------+
| JSON Size      | Media Type Size      | Payload Size   |
| 2 bytes        | 1 byte               | 5 bytes        |
+----------------+----------------------+----------------+
| JSON | Media Type | Payload                            |
+-------------------------------------------------------+
```

8バイト固定長ヘッダーによって、後続するJSON・Media Type・Payloadのサイズを通知します。

これにより、TCPの `recv()` が送信単位と一致しないことを前提として、必要なデータ量を正確に受信できるようにしています。

---

## Technologies

* Python 3
* TCP Socket
* FFmpeg
* ffprobe
* Threading
* ThreadPoolExecutor
* JSON
* UUID
* Python Standard Library
* Git / GitHub

---

## Repository Structure

```text
video-compressor/
├── stage1/
│   ├── client.py
│   ├── server.py
│   ├── protocol.py
│   └── README.md
│
├── stage2/
│   ├── client.py
│   ├── server.py
│   ├── protocol.py
│   ├── transport.py
│   ├── ffmpeg_service.py
│   ├── request_processor.py
│   ├── job_manager.py
│   ├── storage.py
│   └── README.md
│
└── README.md
```

---

## What I Learned

このプロジェクトでは、Webフレームワークによって抽象化されることの多いネットワーク通信やバックエンド処理を、TCPソケットから段階的に実装しました。

特に以下について理解を深めました。

* TCP通信とストリーム指向のデータ転送
* 固定長ヘッダーを利用した独自プロトコル設計
* 大容量ファイルの分割送受信
* 不完全なファイルを残さないファイル管理
* クライアント・サーバーアーキテクチャ
* FFmpegを利用したサーバーサイド動画処理
* Jobによる非同期処理の設計
* スレッドプールによる並行処理
* Lockによる共有データの排他制御
* ポーリングによる非同期処理結果の取得
* エラーレスポンス設計
* サーバーリソースとストレージの管理

低レイヤーの通信処理から動画処理までを実装することで、バックエンドアプリケーションで利用される通信・非同期処理・ファイル管理の基礎を学ぶことを目的としています。

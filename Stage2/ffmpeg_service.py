import subprocess

from pathlib import Path


def run_ffmpeg(
        input_path: Path,
        output_path: Path,
        ffmpeg_args: list[str]
) -> None:

    if not input_path.is_file():
        raise ValueError("存在しないファイルです。")

    # ffmpegコマンドの構造 : ffmpeg [グローバルオプション] -i [入力ファイル] [コーデック等のオプション] [出力ファイル]
    command = [
        "ffmpeg",
        "-y",       # 出力ファイルが既に存在していた場合、確認せずに上書きする
        "-i",
        str(input_path),
        *ffmpeg_args,
        str(output_path)
    ]

    subprocess.run(
        args=command,
        check=True      # プロセスが非0の終了コードで終了するとCalledProcessError例外が送出される
    )

    if not output_path.is_file():
        raise RuntimeError("出力ファイルが生成されませんでした。")


def compress_video(
        input_path: Path,
        output_path: Path
) -> None:

    ffmpeg_args = [
        "-c:v", "libx264",      # codec video:動画をどの方式で圧縮するか
        "-crf", "23",           # CRF:画質とファイルサイズのバランス
        "-preset", "medium"     # preset:圧縮処理にどれくらいの時間を使って効率よく圧縮するか
    ]

    run_ffmpeg(
        input_path=input_path,
        output_path=output_path,
        ffmpeg_args=ffmpeg_args
    )


def resize_video(
        input_path: Path,
        output_path: Path,
        width: int,
        height: int
) -> None:

    if width <= 0 or height <= 0:
        raise ValueError("widthとheightは1以上である必要があります。")

    ffmpeg_args = [
        "-vf", f"scale={width}:{height}",   # video filter: 解像度の変更
        "-c:v", "libx264",
        "-c:a", "copy"  # 音声はそのままコピー
    ]

    run_ffmpeg(
        input_path=input_path,
        output_path=output_path,
        ffmpeg_args=ffmpeg_args
    )


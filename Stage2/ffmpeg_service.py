import json
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


def get_video_resolution(input_path: Path) -> tuple[int, int]:
    if not input_path.is_file():
        raise ValueError("存在しないファイルです。")

    command = [
        "ffprobe",       # 動画ファイルについての情報を調べるためのコマンド
        "-v", "error",      # エラー以外の余計なログを表示しない
        "-select_streams", "v:0",       # 最初の映像ストリームを対象にする
        "-show_entries", "stream=width,height",   # widthとheightだけ取得
        "-of", "json",      # 結果をjsonで取得
        str(input_path)
    ]

    result = subprocess.run(
        args=command,
        check=True,
        capture_output=True,    # 標準出力に出した結果をPythonで受け取る
        text=True   # bytesではなく文字列として受け取る
    )

    data = json.loads(result.stdout)

    width = data["streams"][0]["width"]
    height = data["streams"][0]["height"]

    return width, height


def change_aspect_ratio(
        input_path: Path,
        output_path: Path,
        aspect_width: int,
        aspect_height: int
) -> None:

    if aspect_width <= 0 or aspect_height <= 0:
        raise ValueError("アスペクト比は1以上である必要があります。")

    width, height = get_video_resolution(input_path)

    current_ratio = width / height

    target_ratio = aspect_width / aspect_height

    if current_ratio > target_ratio:
        # 元動画のほうが横長の場合、左右を削る
        # new_width / height = aspect_width / aspect_height
        new_width = int(target_ratio * height)
        new_height = height
    elif current_ratio < target_ratio:
        # 元動画の方が縦長の場合、上下を削る
        # width / new_height = aspect_width / aspect_height
        new_height = int(width * aspect_height / aspect_width)
        new_width = width
    else:
        new_width = width
        new_height = height

    ffmpeg_args = [
        "-vf", f"crop={new_width}:{new_height}",
        "-c:v", "libx264",
        "-c:a", "copy"
    ]

    run_ffmpeg(
        input_path=input_path,
        output_path=output_path,
        ffmpeg_args=ffmpeg_args
    )

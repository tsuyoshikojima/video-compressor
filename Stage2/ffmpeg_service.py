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


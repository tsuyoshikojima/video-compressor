from pathlib import Path


MAX_STORAGE_SIZE = 4 * 1024 ** 4


class StorageLimitError(Exception):
    """ストレージ容量の上限を超える場合の例外"""
    pass


def get_storage_usage(directories: list[Path]) -> int:
    """サーバーのストレージに保存しているファイル容量を返す"""

    total_size = 0

    for directory in directories:
        for path in directory.iterdir():
            if path.is_file():
                total_size += path.stat().st_size

    return total_size


def check_storage_capacity(
        directories: list[Path],
        incoming_size: int 
) -> None:

    total_size = get_storage_usage(directories)

    if total_size + incoming_size > MAX_STORAGE_SIZE:
        raise StorageLimitError("サーバーのストレージ容量の上限を超えます。")
from enum import IntEnum


HEADER_LENGTH = 4
RESPONSE_SIZE = 16      # ステータスコードを含む16バイトのメッセージ
MAX_FILE_SIZE = 2 ** 32 - 1


class StatusCode(IntEnum):
    SUCCESS = 0
    INCOMPLETE_UPLOAD = 1
    SERVER_ERROR = 2


def encode_file_size(file_size: int) -> bytes:
    """ファイルサイズをヘッダーのプロトコルに合わせてバイト列に変換する"""

    if not 0 <= file_size <= MAX_FILE_SIZE:
        raise ValueError("不正なファイルサイズです。")

    return file_size.to_bytes(
        length=HEADER_LENGTH,
        byteorder="big"
    )


def decode_file_size(header: bytes) -> int:
    """サーバーで受信したヘッダーを整数に戻す"""

    if len(header) != HEADER_LENGTH:
        raise ValueError("不正なヘッダーサイズです。")

    return int.from_bytes(
        bytes=header,
        byteorder="big"
    )


def encode_response(status_code: StatusCode) -> bytes:
    """クライアントへの16バイトのレスポンスを生成する"""
    
    response_header = status_code.to_bytes(
        length=1,
        byteorder="big"
    )

    reserved = (RESPONSE_SIZE - len(response_header))
    response_body = bytes(reserved)

    return response_header + response_body


def decode_response(data: bytes) -> StatusCode:
    """サーバーからのレスポンスをステータスコードに変換する"""

    if len(data) != RESPONSE_SIZE:
        raise ValueError("不正なレスポンスです。")

    return StatusCode(data[0])
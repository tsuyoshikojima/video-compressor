import json


MAX_JSON_SIZE = 2 ** 16 - 1
MAX_MEDIA_TYPE_SIZE = 4
MAX_PAYLOAD_SIZE = 2 ** 40 - 1

HEADER_SIZE = 8


def encode_header(
    json_size: int,
    media_type_size: int,
    payload_size: int
) -> bytes:

    if not 0 <= json_size <= MAX_JSON_SIZE:
        raise ValueError("JSONサイズが不正です。")

    if not 0 <= media_type_size <= MAX_MEDIA_TYPE_SIZE:
        raise ValueError("メディアタイプのサイズが不正です。")

    if not 0 <= payload_size <= MAX_PAYLOAD_SIZE:
        raise ValueError("ペイロードのサイズが不正です。")

    json_size_bytes = json_size.to_bytes(
        length=2,
        byteorder="big"
    )

    media_type_size_bytes = media_type_size.to_bytes(
        length=1,
        byteorder="big"
    )

    payload_size_bytes = payload_size.to_bytes(
        length=5,
        byteorder="big"
    )

    return json_size_bytes + media_type_size_bytes + payload_size_bytes


def decode_header(header: bytes) -> tuple[int, int, int]:
    if len(header) != HEADER_SIZE:
        raise ValueError("ヘッダーのサイズが不正です。")

    json_size = int.from_bytes(
        bytes=header[:2],
        byteorder="big"
    )

    media_type_size = header[2]

    if not 0 <= media_type_size <= MAX_MEDIA_TYPE_SIZE:
        # 1バイトは0〜255の数字を表現可能だがプロトコルの仕様上0〜4に制限する
        raise ValueError("メディアタイプのサイズが不正です。")

    payload_size = int.from_bytes(
        bytes=header[3:],
        byteorder="big"
    )

    return json_size, media_type_size, payload_size


def encode_json(data: dict) -> bytes:
    json_data = json.dumps(data)

    json_bytes = json_data.encode("utf-8")

    if len(json_bytes) > MAX_JSON_SIZE:
        raise ValueError("JSONのサイズが大きすぎます。")

    return json_bytes


def decode_json(data: bytes) -> dict:
    if len(data) > MAX_JSON_SIZE:
        raise ValueError("JSONのサイズが大きすぎます。")

    json_data = json.loads(data.decode("utf-8"))

    if not isinstance(json_data, dict):
        raise ValueError("不正なJSONです。")

    return json_data


def encode_media_type(media_type: str) -> bytes:
    media_type_bytes = media_type.encode("utf-8")

    if len(media_type_bytes) > MAX_MEDIA_TYPE_SIZE:
        raise ValueError("不正なメディアタイプです。")
    
    return media_type_bytes


def decode_media_type(media_type_bytes: bytes) -> str:
    if len(media_type_bytes) > MAX_MEDIA_TYPE_SIZE:
        raise ValueError("不正なメディアタイプです。")

    return media_type_bytes.decode("utf-8")
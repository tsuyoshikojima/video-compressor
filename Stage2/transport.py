import socket
import uuid

from pathlib import Path


from protocol import (
    decode_header,
    decode_json,
    decode_media_type,
    encode_header,
    encode_json,
    encode_media_type,
    HEADER_SIZE
)


CHUNK_SIZE = 1400

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


def recv_exact(
        connection: socket.socket,
        data_size: int
) -> bytes:

    if data_size < 0:
        raise ValueError("data_sizeは0以上である必要がります。")
    
    remaining_size = data_size
    received_data = bytearray()

    while remaining_size > 0:
        chunk = connection.recv(remaining_size)

        if not chunk:
            raise ConnectionError("データ受信中に切断されました。")

        received_data += chunk

        remaining_size -= len(chunk)

    return bytes(received_data)


def recv_mmp_message(connection: socket.socket) -> tuple[dict, str | None, Path | None]:

    header_bytes = recv_exact(
        connection=connection,
        data_size=HEADER_SIZE
    )

    json_size, media_type_size, payload_size = decode_header(header_bytes)

    json_bytes = recv_exact(
        connection=connection,
        data_size=json_size
    )

    json_data = decode_json(json_bytes)

    if media_type_size == 0 and payload_size == 0:
        return json_data, None, None

    if media_type_size == 0 or payload_size == 0:
        raise ValueError("不正なMMPメッセージです。")

    media_type_bytes = recv_exact(
        connection=connection,
        data_size=media_type_size
    )

    media_type = decode_media_type(media_type_bytes)

    remaining_size = payload_size

    file_id = uuid.uuid4().hex
    temp_path = UPLOAD_DIR / f"{file_id}.temp"
    saved_path = UPLOAD_DIR / f"{file_id}.{media_type}"

    try:
        with open(temp_path, "wb") as f:
            while remaining_size > 0:
                data_bytes = connection.recv(min(CHUNK_SIZE, remaining_size))

                if not data_bytes:
                    raise ConnectionError("データ受信中に切断されました。")

                f.write(data_bytes)

                remaining_size -= len(data_bytes)

        temp_path.rename(saved_path)

    finally:
        # ファイルのアップロードに失敗した場合、temp_pathが残るので削除する
        temp_path.unlink(missing_ok=True)

    return json_data, media_type, saved_path


def send_mmp_message(
        connection: socket.socket,
        json_data: dict,
        media_type: str | None,
        payload: Path | None
) -> None:

    json_bytes = encode_json(json_data)
    json_size = len(json_bytes)

    if media_type is None and payload is None:
        media_type_size = 0
        payload_size = 0

        header = encode_header(
            json_size=json_size,
            media_type_size=media_type_size,
            payload_size=payload_size
        )

        connection.sendall(header)
        connection.sendall(json_bytes)

        return

    if media_type is None or payload is None:
        raise ValueError("不正なMMPメッセージです。")

    media_type_bytes = encode_media_type(media_type)
    media_type_size = len(media_type_bytes)

    payload_size = payload.stat().st_size

    if payload_size == 0:
        raise ValueError("不正なペイロードです。")

    header = encode_header(
        json_size=json_size,
        media_type_size=media_type_size,
        payload_size=payload_size
    )

    remaining_size = payload_size

    with open(payload, "rb") as f:
        connection.sendall(header)
        connection.sendall(json_bytes)
        connection.sendall(media_type_bytes)

        while remaining_size > 0:
            chunk = f.read(min(CHUNK_SIZE, remaining_size))

            if not chunk:
                raise IOError("ファイルのデータ読み取りに失敗しました。")

            connection.sendall(chunk)

            remaining_size -= len(chunk)
    
import base64
import hashlib
import io
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

import requests as http_requests
from cryptography.hazmat.primitives import hashes
from django.conf import settings
from django.http import JsonResponse
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bookings.models import Booking
from guests.models import Guest
from .models import DogovirText, TextStyle

logger = logging.getLogger(__name__)

FONT_DIR = Path(getattr(settings, "DOGOVIR_FONT_DIR"))

try:
    pdfmetrics.registerFont(
        TTFont("NotoSans", str(FONT_DIR / "MazzardH-Regular.ttf"))
    )
    pdfmetrics.registerFont(
        TTFont("NotoSans-Bold", str(FONT_DIR / "NotoSans-Bold.ttf"))
    )
    pdfmetrics.registerFont(
        TTFont("Brice", str(FONT_DIR / "Brice-Regular.ttf"))
    )
    _BOLD = "NotoSans-Bold"
    _NORMAL = "NotoSans"
    _BRICE = "Brice"
except Exception:
    _BOLD = "Helvetica-Bold"
    _NORMAL = "Helvetica"
    _BRICE = "Helvetica-Bold"

title_brice = ParagraphStyle(
    "TitleBrice",
    fontName=_BRICE,
    fontSize=22,
    alignment=TA_LEFT,
)

right_bold = ParagraphStyle(
    "RightBold",
    fontName=_BOLD,
    fontSize=14,
    alignment=TA_RIGHT,
)

right_normal = ParagraphStyle(
    "RightNormal",
    fontName=_NORMAL,
    fontSize=12,
    alignment=TA_RIGHT,
)

left_bold = ParagraphStyle(
    "LeftBold",
    fontName=_BOLD,
    fontSize=14,
    alignment=TA_LEFT,
    spaceAfter=6,
)

left_normal = ParagraphStyle(
    "LeftNormal",
    fontName=_NORMAL,
    fontSize=12,
    alignment=TA_LEFT,
    spaceAfter=10,
)

left_semibold = ParagraphStyle(
    "LeftSemiBold",
    fontName=_BOLD,
    fontSize=12,
    alignment=TA_LEFT,
    spaceAfter=6,
)

STYLE_MAP = {
    TextStyle.LEFT_BOLD: left_bold,
    TextStyle.LEFT_SEMI_BOLD: left_semibold,
    TextStyle.LEFT_NORMAL: left_normal,
}


def _pdf_dir():
    d = Path(
        getattr(
            settings,
            "DOGOVIR_PDF_DIR",
            Path(settings.BASE_DIR) / "contracts",
        )
    )
    d.mkdir(parents=True, exist_ok=True)
    return d


def _drive_service():
    creds_path = getattr(settings, "GOOGLE_CREDENTIALS", None)

    if not creds_path:
        raise RuntimeError(
            "GOOGLE_CREDENTIALS not configured in settings"
        )

    creds = service_account.Credentials.from_service_account_file(
        str(creds_path),
        scopes=[
            "https://www.googleapis.com/auth/drive"
        ],
    )

    return build(
        "drive",
        "v3",
        credentials=creds,
        cache_discovery=False,
    )


def _pdf_hash_hex(pdf_bytes):
    digest = hashes.Hash(hashes.SHA256())
    digest.update(pdf_bytes)
    return digest.finalize().hex()


def _create_drive_folder(service, parent_id, folder_name):
    meta = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }

    folder = service.files().create(
        body=meta,
        fields="id,webViewLink",
        supportsAllDrives=True,
    ).execute()

    return (
        folder["id"],
        folder.get("webViewLink", ""),
    )


def _upload_to_drive(
    service,
    file_bytes,
    filename,
    folder_id,
    mime_type="application/pdf",
):
    media = MediaIoBaseUpload(
        io.BytesIO(file_bytes),
        mimetype=mime_type,
    )

    file_meta = {
        "name": filename,
        "parents": [folder_id],
    }

    file = service.files().create(
        body=file_meta,
        media_body=media,
        fields="id,webViewLink",
        supportsAllDrives=True,
    ).execute()

    return {
        "file_id": file["id"],
        "file_link": file["webViewLink"],
    }


def _send_telegram(data):
    token = getattr(
        settings,
        "TELEGRAM_BOT_TOKEN",
        None,
    )

    group_id = getattr(
        settings,
        "TELEGRAM_GROUP_ID",
        None,
    )

    if not token or not group_id:
        logger.warning(
            "Telegram credentials not configured"
        )
        return False

    message = (
        f"<b>Договір <u>№LK-{data['year']}-{data['id']}</u> підписано</b>\n\n"
        f"<b>Дані про гостя</b>\n"
        f"\tПІБ: {data['guest_name']}\n"
        f"\tДата народження: {data['guest_birthday']}\n"
        f"\tТелефон: {data['guest_phone']}\n"
        f"\tПаспортні дані: {data['guest_document']}\n"
        f"\n<b>Дані про бронювання</b>\n"
        f"\tБудинок: {data['house']}\n"
        f"\tЗаїзд: {data['check_in']}\n"
        f"\tВиїзд: {data['check_out']}\n"
        f"\n<b>Підписано:</b> {data['timestamp']}"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "Google Drive",
                    "url": data["drive_url"],
                }
            ]
        ]
    }

    payload = {
        "chat_id": group_id,
        "text": message,
        "parse_mode": "HTML",
        "reply_markup": keyboard,
    }

    thread_id = getattr(
        settings,
        "TELEGRAM_THREAD_ID",
        None,
    )

    if thread_id:
        payload["message_thread_id"] = int(thread_id)

    try:
        response = http_requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json=payload,
            timeout=10,
        )

        logger.warning(
            "Telegram raw: %s",
            response.text,
        )

        response.raise_for_status()

        result = response.json()

        if result.get("ok"):
            logger.info(
                "Telegram sent: message_id=%s",
                result.get("result", {}).get("message_id"),
            )
            return True

        logger.warning(
            "Telegram API error: %s",
            result.get("description"),
        )

        return False

    except http_requests.exceptions.RequestException as exc:
        logger.error(
            "Telegram request failed: %s",
            exc,
        )
        return False


def _custom_code(input_str, length=6):
    digest = hashlib.sha256(
        input_str.encode("utf-8")
    ).digest()

    num = int.from_bytes(
        digest[:8],
        byteorder="big",
    )

    alphabet = (
        "01234567890123456789"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    )

    base = len(alphabet)
    code = ""

    while num > 0:
        num, remainder = divmod(
            num,
            base,
        )
        code = (
            alphabet[remainder]
            + code
        )

    return code[:length]


def _generate_pdf(filepath, data):
    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    base_styles = getSampleStyleSheet()
    base_styles["Normal"].fontName = _NORMAL

    elements = []

    header = Table(
        [
            [
                Paragraph(
                    "LAZNI KYIV",
                    title_brice,
                ),
                [
                    Paragraph(
                        "<b>ДОГОВІР</b>",
                        right_bold,
                    ),
                    Spacer(1, 6),
                    Paragraph(
                        f"№ LK-{datetime.now().year}-{data['id']}",
                        right_normal,
                    ),
                    Paragraph(
                        "м. Київ",
                        right_normal,
                    ),
                    Paragraph(
                        data["date"],
                        right_normal,
                    ),
                ],
            ]
        ],
        colWidths=[
            doc.width * 0.5,
            doc.width * 0.5,
        ],
    )

    header.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "ALIGN",
                    (1, 0),
                    (1, 0),
                    "RIGHT",
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    12,
                ),
            ]
        )
    )

    elements.append(header)

    elements.append(
        Paragraph(
            f"Цей Договір укладено між Lazni Kyiv "
            f"(далі - комплекс) та "
            f"{data['guest_name']} (далі - Гість)",
            left_normal,
        )
    )

    elements.append(
        Spacer(1, 20)
    )

    elements.append(
        Paragraph(
            "Дані про гостя",
            left_bold,
        )
    )

    elements.append(
        Spacer(1, 10)
    )

    elements.append(
        Paragraph(
            f"ПІБ: {data.get('guest_name', '—')}",
            left_normal,
        )
    )

    elements.append(
        Paragraph(
            f"Номер телефону: "
            f"{data.get('guest_phone', '—')}",
            left_normal,
        )
    )

    elements.append(
        Paragraph(
            f"Дата народження: "
            f"{data.get('guest_birthday', '—')}",
            left_normal,
        )
    )

    elements.append(
        Paragraph(
            f"Паспортні дані: "
            f"{data.get('guest_document', '—')}",
            left_normal,
        )
    )

    elements.append(
        Spacer(1, 10)
    )

    elements.append(
        Paragraph(
            "Дані про бронювання",
            left_bold,
        )
    )

    elements.append(
        Spacer(1, 10)
    )

    elements.append(
        Paragraph(
            f"Дата та час заїзду: "
            f"{data.get('check_in', '—')}",
            left_normal,
        )
    )

    elements.append(
        Paragraph(
            f"Дата та час виїзду: "
            f"{data.get('check_out', '—')}",
            left_normal,
        )
    )

    elements.append(
        Paragraph(
            f"Будинок: "
            f"{data.get('house', '—')}",
            left_normal,
        )
    )

    elements.append(
        Spacer(1, 20)
    )

    for entry in DogovirText.objects.all():
        style = STYLE_MAP.get(
            entry.style,
            left_normal,
        )

        safe = (
            entry.title
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        elements.append(
            Paragraph(
                safe,
                style,
            )
        )

        elements.append(
            Spacer(1, 4)
        )

    if data.get("signature"):
        elements.append(
            Spacer(1, 30)
        )

        elements.append(
            Paragraph(
                "Підпис гостя:",
                left_bold,
            )
        )

        try:
            sig_data = data["signature"]

            if "," in sig_data:
                sig_data = sig_data.split(
                    ",",
                    1,
                )[1]

            sig_img = Image(
                io.BytesIO(
                    base64.b64decode(
                        sig_data
                    )
                ),
                width=150,
                height=75,
            )

            elements.append(sig_img)

            elements.append(
                Spacer(1, 10)
            )

            elements.append(
                Paragraph(
                    f"Дата та час підписання: "
                    f"{data['time']}",
                    left_normal,
                )
            )

        except Exception as exc:
            logger.error(
                "Signature processing error: %s",
                exc,
            )

            elements.append(
                Paragraph(
                    "Помилка обробки підпису",
                    left_normal,
                )
            )

    doc.build(elements)


class DogovirTextView(APIView):

    permission_classes = []

    def get(self, request):
        text = [
            {
                "title": entry.title,
                "style": entry.style,
            }
            for entry in DogovirText.objects.all()
        ]

        return Response(
            {
                "status": "ok",
                "text": text,
            }
        )


class ContractsView(APIView):

    permission_classes = [
        IsAuthenticated
    ]

    def get(self, request):
        if not request.user.has_perm(
            "cloud.view_contract"
        ):
            return Response(
                {
                    "error": "Forbidden"
                },
                status=403,
            )

        bookings = Booking.objects.values(
            "dogovir",
            "guest",
            "id",
        )

        guests = Guest.objects.values(
            "id",
            "name",
        )

        guests_map = {
            guest["id"]: guest["name"]
            for guest in guests
        }

        result = []

        for booking in bookings:
            dogovir = booking.get(
                "dogovir"
            ) or {}

            if not dogovir.get(
                "drive_url"
            ):
                continue

            result.append(
                {
                    "id": (
                        f"LK-{_custom_code(str(booking['id']))}"
                    ),
                    "drive_url": dogovir[
                        "drive_url"
                    ],
                    "timestamp": dogovir.get(
                        "timestamp"
                    ),
                    "guest_name": guests_map.get(
                        booking["guest"],
                        "—",
                    ),
                }
            )

        return Response(result)

    def post(self, request):
        data = request.data

        booking_id = data.get(
            "booking_id"
        )

        if not booking_id:
            return Response(
                {
                    "error": "booking_id is required"
                },
                status=400,
            )

        dogovir_id = data.get(
            "id",
            "—",
        )

        now = datetime.now()

        time_str = now.strftime(
            "%d.%m.%Y %H:%M:%S"
        )

        year = now.year

        filename = (
            f"LK-{year}-{dogovir_id}.pdf"
        )

        pdf_data = {
            "id": dogovir_id,
            "date": now.strftime(
                "%d.%m.%Y"
            ),
            "guest_name": data.get(
                "guest_name",
                "—",
            ),
            "guest_phone": data.get(
                "guest_phone",
                "—",
            ),
            "guest_birthday": data.get(
                "guest_birthday",
                "—",
            ),
            "guest_document": data.get(
                "guest_document",
                "—",
            ),
            "house": data.get(
                "house",
                "—",
            ),
            "check_in": data.get(
                "check_in",
                "—",
            ),
            "check_out": data.get(
                "check_out",
                "—",
            ),
            "signature": data.get(
                "signature"
            ),
            "time": time_str,
        }

        server_filename = (
            f"{uuid.uuid4().hex}.pdf"
        )

        local_path = (
            _pdf_dir()
            / server_filename
        )

        try:
            _generate_pdf(
                local_path,
                pdf_data,
            )

        except Exception as exc:
            logger.exception(
                "PDF generation failed"
            )

            return Response(
                {
                    "status": "false",
                    "error": str(exc),
                },
                status=500,
            )

        try:
            with open(
                local_path,
                "rb",
            ) as file:
                pdf_bytes = file.read()

            pdf_hash = _pdf_hash_hex(
                pdf_bytes
            )

        except Exception as exc:
            logger.exception(
                "PDF read/hash failed"
            )

            return Response(
                {
                    "status": "false",
                    "error": str(exc),
                },
                status=500,
            )

        drive_error = False
        drive_pdf_uploaded = False
        drive_signature_uploaded = False
        pdf_info = None

        try:
            service = _drive_service()

            parent_id = os.getenv(
                "DOGOVIR_DRIVE_PARENT_ID"
            )

            if not parent_id:
                raise RuntimeError(
                    "DOGOVIR_DRIVE_PARENT_ID is not configured"
                )

            folder_id, _ = (
                _create_drive_folder(
                    service,
                    parent_id,
                    f"LK-{year}-{dogovir_id}",
                )
            )

            pdf_info = _upload_to_drive(
                service,
                pdf_bytes,
                filename,
                folder_id,
            )

            drive_pdf_uploaded = True

            sig_doc = {
                "pdf_hash": pdf_hash,
                "hash_algorithm": "SHA-256",
                "timestamp": (
                    datetime.utcnow()
                    .isoformat()
                    + "Z"
                ),
                "metadata": {
                    "guest_name": data.get(
                        "guest_name"
                    ),
                    "dogovir_id": dogovir_id,
                    "date": pdf_data[
                        "date"
                    ],
                },
            }

            sig_filename = filename.replace(
                ".pdf",
                ".json",
            )

            sig_local_path = (
                _pdf_dir()
                / sig_filename
            )

            with open(
                sig_local_path,
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    sig_doc,
                    file,
                    indent=2,
                    ensure_ascii=False,
                )

            _upload_to_drive(
                service,
                json.dumps(
                    sig_doc,
                    indent=2,
                    ensure_ascii=False,
                ).encode("utf-8"),
                sig_filename,
                folder_id,
                mime_type="application/json",
            )

            drive_signature_uploaded = True

        except Exception:
            drive_error = True

            logger.exception(
                "Google Drive upload failed"
            )

        dogovir_data = {
            "timestamp": time_str,
            "drive_error": drive_error,
        }

        if pdf_info:
            dogovir_data["drive_url"] = (
                "https://drive.google.com/file/d/"
                f"{pdf_info['file_id']}/view"
            )

        if drive_error:
            dogovir_data[
                "drive_pdf_uploaded"
            ] = drive_pdf_uploaded

            dogovir_data[
                "drive_signature_uploaded"
            ] = drive_signature_uploaded

        try:
            Booking.objects.filter(
                pk=booking_id
            ).update(
                dogovir=dogovir_data
            )

        except Exception as exc:
            logger.exception(
                "Booking update failed"
            )

            return Response(
                {
                    "status": "false",
                    "error": str(exc),
                },
                status=500,
            )

        update_data = {
            "link": (
                pdf_info["file_id"]
                if pdf_info
                else None
            ),
            "pdf": server_filename.replace(
                ".pdf",
                "",
            ),
            "ts": time_str,
            "drive_error": drive_error,
            "drive_pdf_uploaded": (
                drive_pdf_uploaded
            ),
            "drive_signature_uploaded": (
                drive_signature_uploaded
            ),
        }

        try:
            _send_telegram(
                {
                    "id": dogovir_id,
                    "year": year,
                    "guest_name": data.get(
                        "guest_name",
                        "—",
                    ),
                    "guest_phone": data.get(
                        "guest_phone",
                        "—",
                    ),
                    "guest_birthday": data.get(
                        "guest_birthday",
                        "—",
                    ),
                    "guest_document": data.get(
                        "guest_document",
                        "—",
                    ),
                    "house": data.get(
                        "house",
                        "—",
                    ),
                    "check_in": data.get(
                        "check_in",
                        "—",
                    ),
                    "check_out": data.get(
                        "check_out",
                        "—",
                    ),
                    "timestamp": time_str,
                    "drive_url": (
                        f"https://drive.google.com/file/"
                        f"d/{pdf_info['file_id']}/view"
                        if pdf_info
                        else None
                    ),
                    "drive_error": drive_error,
                }
            )

        except Exception as exc:
            logger.warning(
                "Telegram notification failed: %s",
                exc,
            )

        return Response(
            update_data,
            status=201,
        )
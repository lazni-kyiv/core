# import requests
# from django.conf import settings
#
#
# class ZohoMailService:
#
#     BASE_URL = "https://mail.zoho.com/api/accounts"
#
#     @classmethod
#     def send(cls, to: str, subject: str, content: str, cc: str = None):
#         url = f"{cls.BASE_URL}/{settings.ZOHO_ACCOUNT_ID}/messages"
#
#         payload = {
#             "fromAddress": settings.ZOHO_FROM_EMAIL,
#             "toAddress":   to,
#             "subject":     subject,
#             "content":     content,
#             "askReceipt":  "no",
#         }
#         if cc:
#             payload["ccAddress"] = cc
#
#         headers = {
#             "Accept":        "application/json",
#             "Content-Type":  "application/json",
#             "Authorization": f"Zoho-oauthtoken {settings.ZOHO_ACCESS_TOKEN}",
#         }
#
#         response = requests.post(url, json=payload, headers=headers)
#         response.raise_for_status()
#         return response.json()
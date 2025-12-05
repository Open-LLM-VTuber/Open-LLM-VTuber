import hashlib
import hmac
import json
import time
from datetime import datetime, timezone

import httpx
from loguru import logger

from .translate_interface import TranslateInterface


def sign(key, msg):
    """Generate HMAC-SHA256 signature"""
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


class TencentTranslate(TranslateInterface):
    def __init__(
        self,
        secret_id: str,
        secret_key: str,
        token: str = "",
        region: str = "ap-guangzhou",
        source_lang: str = "zh",
        target_lang: str = "ja",
    ):
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.token = token
        self.region = region
        self.service = "tmt"
        self.host = "tmt.tencentcloudapi.com"
        self.version = "2018-03-21"
        self.action = "TextTranslate"
        self.algorithm = "TC3-HMAC-SHA256"
        self.source_lang = source_lang
        self.target_lang = target_lang

    def create_signature(self, date, service):
        """Create signature"""
        secret_date = sign(("TC3" + self.secret_key).encode("utf-8"), date)
        secret_service = sign(secret_date, service)
        secret_signing = sign(secret_service, "tc3_request")
        return secret_signing

    def _prepare_headers(self, payload: str, timestamp: int, date: str) -> dict:
        """Prepare request headers"""
        ct = "application/json; charset=utf-8"
        canonical_uri = "/"
        canonical_querystring = ""
        canonical_headers = (
            f"content-type:{ct}\nhost:{self.host}\nx-tc-action:{self.action.lower()}\n"
        )
        signed_headers = "content-type;host;x-tc-action"
        hashed_request_payload = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        canonical_request = "\n".join(
            [
                "POST",
                canonical_uri,
                canonical_querystring,
                canonical_headers,
                signed_headers,
                hashed_request_payload,
            ]
        )

        credential_scope = f"{date}/{self.service}/tc3_request"
        hashed_canonical_request = hashlib.sha256(
            canonical_request.encode("utf-8")
        ).hexdigest()
        string_to_sign = f"{self.algorithm}\n{timestamp}\n{credential_scope}\n{hashed_canonical_request}"

        secret_signing = self.create_signature(date, self.service)
        signature = hmac.new(
            secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        authorization = f"{self.algorithm} Credential={self.secret_id}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"

        headers = {
            "Authorization": authorization,
            "Content-Type": ct,
            "Host": self.host,
            "X-TC-Action": self.action,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Version": self.version,
        }
        if self.region:
            headers["X-TC-Region"] = self.region
        if self.token:
            headers["X-TC-Token"] = self.token

        return headers

    def translate(self, text: str) -> str:
        """Translate text"""
        timestamp = int(time.time())
        date = datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d")

        payload = json.dumps(
            {
                "SourceText": text,
                "Source": self.source_lang,
                "Target": self.target_lang,
                "ProjectId": 0,
            }
        )

        headers = self._prepare_headers(payload, timestamp, date)

        try:
            response = httpx.post(
                url="https://" + self.host, headers=headers, data=payload
            )
            res = response.json()
            logger.info(f"Request successful: {res}")
            return res.get("Response", {}).get("TargetText", "Translation failed")
        except Exception as e:
            logger.critical(f"API call error: {e}")
            raise e

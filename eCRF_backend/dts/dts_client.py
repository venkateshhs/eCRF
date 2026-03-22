from __future__ import annotations

from typing import Any, Dict, Optional
import requests

from .dts_settings import DTS_BASE_URL, DTS_TOKEN


class DTSClientError(Exception):
    pass


class DTSClient:
    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None, timeout: int = 20):
        self.base_url = (base_url or DTS_BASE_URL).rstrip("/")
        self.token = token or DTS_TOKEN
        self.timeout = timeout

    def _headers(self, content_type: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
        }
        if self.token:
            headers["X-DumpThings-Token"] = self.token
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def validate_record(self, collection: str, class_name: str, payload: Dict[str, Any]) -> Any:
        r = requests.post(
            f"{self.base_url}/{collection}/validate/record/{class_name}",
            headers=self._headers("application/json"),
            json=payload,
            timeout=self.timeout,
        )
        self._raise(r)
        return r.json()

    def post_record(self, collection: str, class_name: str, payload: Dict[str, Any]) -> Any:
        r = requests.post(
            f"{self.base_url}/{collection}/record/{class_name}",
            headers=self._headers("application/json"),
            json=payload,
            timeout=self.timeout,
        )
        self._raise(r)
        return r.json()

    def get_record(self, collection: str, pid: str) -> Dict[str, Any]:
        r = requests.get(
            f"{self.base_url}/{collection}/record",
            headers=self._headers(),
            params={"pid": pid, "format": "json"},
            timeout=self.timeout,
        )
        self._raise(r)
        return r.json()

    def list_records(self, collection: str, class_name: str, page: int = 1, size: int = 100) -> Dict[str, Any]:
        r = requests.get(
            f"{self.base_url}/{collection}/records/{class_name}",
            headers=self._headers(),
            params={"page": page, "size": size, "format": "json"},
            timeout=self.timeout,
        )
        self._raise(r)
        return r.json()

    def list_records_paginated(self, collection: str, class_name: str, page: int = 1, size: int = 100) -> Any:
        r = requests.get(
            f"{self.base_url}/{collection}/records/p/{class_name}",
            headers=self._headers(),
            params={"page": page, "size": size},
            timeout=self.timeout,
        )
        self._raise(r)
        return r.json()

    @staticmethod
    def _raise(response: requests.Response) -> None:
        if response.ok:
            return
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise DTSClientError(f"DTS error {response.status_code}: {detail}")
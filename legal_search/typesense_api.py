"""Thin REST client cho Typesense (thuan stdlib)."""
import json
import urllib.request
import urllib.error


class Typesense:
    def __init__(self, base: str, api_key: str):
        self.base = base.rstrip("/")
        self.api_key = api_key

    def _req(self, method, path, body=None, raw_body=None, ctype="application/json"):
        url = f"{self.base}{path}"
        headers = {"X-TYPESENSE-API-KEY": self.api_key}
        if raw_body is not None:
            data = raw_body.encode("utf-8")
            headers["Content-Type"] = ctype
        elif body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        else:
            data = None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                text = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8")
            raise RuntimeError(f"Typesense {method} {path} -> {e.code}: {text[:300]}") from None
        return text

    def get_json(self, path):
        return json.loads(self._req("GET", path))

    def create_collection(self, schema):
        return json.loads(self._req("POST", "/collections", body=schema))

    def drop_collection(self, name):
        try:
            return json.loads(self._req("DELETE", f"/collections/{name}"))
        except RuntimeError:
            return None

    def collection_exists(self, name):
        try:
            self.get_json(f"/collections/{name}")
            return True
        except RuntimeError:
            return False

    def import_documents(self, name, docs, action="upsert"):
        """Bulk import JSONL. Tra ve list ket qua tung dong."""
        jsonl = "\n".join(json.dumps(d, ensure_ascii=False) for d in docs)
        text = self._req(
            "POST",
            f"/collections/{name}/documents/import?action={action}",
            raw_body=jsonl,
            ctype="text/plain",
        )
        results = [json.loads(l) for l in text.splitlines() if l.strip()]
        return results

    def get_document(self, name, doc_id):
        return self.get_json(f"/collections/{name}/documents/{doc_id}")

    def update_by_filter(self, name, filter_by, fields):
        """Update-by-query: cap nhat cac field cho moi doc khop filter. Tra {num_updated}."""
        from urllib.parse import urlencode
        qs = urlencode({"filter_by": filter_by})
        return json.loads(self._req("PATCH", f"/collections/{name}/documents?{qs}", body=fields))

    def delete_by_filter(self, name, filter_by):
        """Delete-by-query: xoa moi doc khop filter. Tra {num_deleted}."""
        from urllib.parse import urlencode
        qs = urlencode({"filter_by": filter_by})
        return json.loads(self._req("DELETE", f"/collections/{name}/documents?{qs}"))

    def search(self, name, params):
        from urllib.parse import urlencode
        qs = urlencode(params)
        return self.get_json(f"/collections/{name}/documents/search?{qs}")

    def multi_search(self, searches, common=None):
        body = {"searches": searches}
        from urllib.parse import urlencode
        qs = urlencode(common or {})
        path = f"/multi_search?{qs}" if qs else "/multi_search"
        return json.loads(self._req("POST", path, body=body))

"""
Simple JSON-file-backed data store.

This replaces MongoDB. Each collection is a list of dicts kept in memory
and mirrored to a .json file on disk, so data survives a server restart
without needing any external database to be installed or running.

The collection API (insert_one, find, find_one, update_one, delete_one,
count_documents) matches the small subset of PyMongo's API that app.py
actually uses, so the rest of the backend didn't need to change shape.
"""

import json
import os
import re
import threading
import uuid

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)


class Result:
    def __init__(self, inserted_id=None, modified_count=0, deleted_count=0):
        self.inserted_id = inserted_id
        self.modified_count = modified_count
        self.deleted_count = deleted_count


class JSONCollection:
    """A minimal, file-persisted stand-in for a MongoDB collection."""

    def __init__(self, name):
        self.name = name
        self.path = os.path.join(DATA_DIR, f"{name}.json")
        self.lock = threading.Lock()
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return []
        return []

    def _save(self):
        tmp_path = f"{self.path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.path)

    def insert_one(self, doc):
        with self.lock:
            doc = dict(doc)
            doc["_id"] = uuid.uuid4().hex
            self.data.append(doc)
            self._save()
            return Result(inserted_id=doc["_id"])

    def insert_many(self, docs):
        with self.lock:
            ids = []
            for doc in docs:
                doc = dict(doc)
                doc["_id"] = uuid.uuid4().hex
                self.data.append(doc)
                ids.append(doc["_id"])
            self._save()
            return Result(inserted_id=ids)

    def find_one(self, query=None):
        query = query or {}
        for doc in self.data:
            if self._matches(doc, query):
                return dict(doc)
        return None

    def find(self, query=None):
        query = query or {}
        return [dict(doc) for doc in self.data if self._matches(doc, query)]

    def count_documents(self, query=None):
        query = query or {}
        return sum(1 for doc in self.data if self._matches(doc, query))

    def update_one(self, query, update):
        with self.lock:
            for doc in self.data:
                if self._matches(doc, query):
                    if "$set" in update:
                        doc.update(update["$set"])
                    self._save()
                    return Result(modified_count=1)
            return Result(modified_count=0)

    def delete_one(self, query):
        with self.lock:
            for i, doc in enumerate(self.data):
                if self._matches(doc, query):
                    del self.data[i]
                    self._save()
                    return Result(deleted_count=1)
            return Result(deleted_count=0)

    @staticmethod
    def _matches(doc, query):
        for key, value in query.items():
            if key == "$or":
                if not any(JSONCollection._matches(doc, cond) for cond in value):
                    return False
                continue

            actual = doc.get(key)

            if isinstance(value, dict):
                if "$regex" in value:
                    flags = re.IGNORECASE if value.get("$options") == "i" else 0
                    if not re.search(value["$regex"], str(actual or ""), flags):
                        return False
                elif "$lte" in value:
                    if actual is None or not (actual <= value["$lte"]):
                        return False
                elif "$all" in value:
                    if not all(item in (actual or []) for item in value["$all"]):
                        return False
                else:
                    return False
            else:
                if actual != value:
                    return False
        return True

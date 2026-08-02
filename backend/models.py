try:
    from pymongo import MongoClient
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
    client.server_info()  # Test connection
    db = client["hostel_finder"]
    hostels_collection = db["hostels"]
    users_collection = db["users"]
    reviews_collection = db["reviews"]
    bookings_collection = db["bookings"]
    print("Connected to MongoDB")
except Exception as e:
    print(f"MongoDB not available: {e}. Using in-memory storage for testing.")
    
    # Fallback to in-memory storage
    class MockResult:
        def __init__(self, inserted_id=None, inserted_ids=None, modified_count=0, deleted_count=0):
            self.inserted_id = inserted_id
            self.inserted_ids = inserted_ids or []
            self.modified_count = modified_count
            self.deleted_count = deleted_count

    class MockCollection:
        def __init__(self):
            self.data = []
            self.counter = 1
        
        def insert_one(self, doc):
            doc['_id'] = str(self.counter)
            self.counter += 1
            self.data.append(doc)
            return MockResult(inserted_id=doc['_id'])
        
        def insert_many(self, docs):
            ids = []
            for doc in docs:
                doc['_id'] = str(self.counter)
                self.counter += 1
                self.data.append(doc)
                ids.append(doc['_id'])
            return MockResult(inserted_ids=ids)
        
        def find_one(self, query=None):
            if not query:
                return self.data[0] if self.data else None
            for doc in self.data:
                if self._match_query(doc, query):
                    return doc
            return None
        
        def find(self, query=None):
            if not query:
                return self.data.copy()
            result = []
            for doc in self.data:
                if self._match_query(doc, query):
                    result.append(doc)
            return result
        
        def count_documents(self, query=None):
            if not query:
                return len(self.data)
            count = 0
            for doc in self.data:
                if self._match_query(doc, query):
                    count += 1
            return count
        
        def update_one(self, query, update):
            modified = 0
            for i, doc in enumerate(self.data):
                if self._match_query(doc, query):
                    if '$set' in update:
                        for k, v in update['$set'].items():
                            self.data[i][k] = v
                    modified += 1
                    break
            return MockResult(modified_count=modified)
        
        def delete_one(self, query):
            deleted = 0
            for i, doc in enumerate(list(self.data)):
                if self._match_query(doc, query):
                    self.data.remove(doc)
                    deleted += 1
                    break
            return MockResult(deleted_count=deleted)
        
        def _match_query(self, doc, query):
            for key, value in query.items():
                if key == '$or':
                    # Handle $or queries
                    found = False
                    for or_condition in value:
                        if self._match_query(doc, or_condition):
                            found = True
                            break
                    if not found:
                        return False
                elif key in doc:
                    if key == '_id' and not isinstance(value, str):
                        # Accept ObjectId-like values by stringifying
                        value = str(value)
                    if isinstance(value, dict):
                        if '$regex' in value:
                            # Simple regex simulation
                            import re
                            pattern = value['$regex']
                            flags = re.IGNORECASE if value.get('$options') == 'i' else 0
                            if not re.search(pattern, str(doc[key]), flags):
                                return False
                        elif '$lte' in value:
                            if not (doc[key] <= value['$lte']):
                                return False
                        elif '$all' in value:
                            if not all(item in doc.get(key, []) for item in value['$all']):
                                return False
                        else:
                            # Unsupported operator in mock
                            return False
                    else:
                        if doc[key] != value:
                            return False
                else:
                    return False
            return True
    
    hostels_collection = MockCollection()
    users_collection = MockCollection()
    reviews_collection = MockCollection()
    bookings_collection = MockCollection()

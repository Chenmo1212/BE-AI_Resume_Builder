from app import mongo
from datetime import datetime
from bson import ObjectId


def _convert_id_type(data):
    if data is not None and '_id' in data:
        data['_id'] = str(data['_id'])
    return data


class BaseManager:
    def __init__(self, collection_name):
        self.collection = mongo.db[collection_name]

    def create(self, data):
        current_time = datetime.now()
        data.update({
            "create_time": current_time,
            "update_time": current_time,
            "delete_time": None,
            "is_delete": False,
            "is_show": True
        })
        result = self.collection.insert_one(data)
        return str(result.inserted_id)

    def update(self, document_id, update_data):
        current_time = datetime.now()
        update_data["update_time"] = current_time
        if '_id' in update_data:
            del update_data['_id']

        result = self.collection.update_one({"_id": ObjectId(document_id)}, {"$set": update_data})
        return result.modified_count

    def delete(self, document_id):
        current_time = datetime.now()
        result = self.collection.update_one({"_id": ObjectId(document_id)},
                                            {"$set": {"delete_time": current_time, "is_delete": True}})
        return result.modified_count

    def get(self, document_id, **query_kwargs):
        document_data = self.collection.find_one({"_id": ObjectId(document_id), **query_kwargs})
        return _convert_id_type(document_data)

    def list(self):
        return [_convert_id_type(doc) for doc in self.collection.find({"is_delete": False})]


class ResumeManager(BaseManager):
    def __init__(self):
        super().__init__('resume')

    def create(self, data):
        data.update({
            "is_raw": data.get('is_raw', True),
            "raw_id": data.get('raw_id', ""),
            "job_id": data.get('job_id', "")
        })
        return super().create(data)


class JobManager(BaseManager):
    def __init__(self):
        super().__init__('job')


class TaskManager(BaseManager):
    def __init__(self):
        super().__init__('task')

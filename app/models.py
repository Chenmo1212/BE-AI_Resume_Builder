from app import mongo
from datetime import datetime
from bson import ObjectId


class Message:
    def __init__(self, name, email, website, content, agent, create_time=None, update_time=None,
                 admin_time=None, delete_time=None, is_delete=False, is_show=False, id=None):
        self.id = ObjectId(id)
        self.name = name
        self.email = email
        self.website = website
        self.content = content
        self.agent = agent
        self.create_time = create_time
        self.update_time = update_time
        self.admin_time = admin_time
        self.delete_time = delete_time
        self.is_delete = is_delete
        self.is_show = is_show

    def save(self):
        current_time = datetime.now()
        result = mongo.db.messages.insert_one({
            'name': self.name,
            'email': self.email,
            'website': self.website,
            'content': self.content,
            'agent': self.agent,
            'create_time': self.create_time or current_time,
            'update_time': self.update_time or current_time,
            'admin_time': self.admin_time or current_time,
            'delete_time': self.delete_time or current_time,
            'is_delete': self.is_delete,
            'is_show': self.is_show
        })
        inserted_id = str(result.inserted_id)
        return inserted_id

    def delete(self):
        mongo.db.messages.delete_one({'_id': ObjectId(self.id)})

    @staticmethod
    def get_all():
        return mongo.db.messages.find()

    @staticmethod
    def get_visible_list():
        return mongo.db.messages.find({'is_show': True})


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
        return result.inserted_id

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

    def get(self, document_id):
        document_data = self.collection.find_one({"_id": ObjectId(document_id)})
        return _convert_id_type(document_data)

    def list(self):
        return [_convert_id_type(doc) for doc in self.collection.find({"is_delete": False})]


class ResumeManager(BaseManager):
    def __init__(self):
        super().__init__('resume')


class JobManager(BaseManager):
    def __init__(self):
        super().__init__('job')

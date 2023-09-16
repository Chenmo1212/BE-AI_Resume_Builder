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


class ResumeManager:
    def __init__(self):
        self.collection = mongo.db.resume

    def create_resume(self, resume_data):
        current_time = datetime.now()
        resume_data.update({
            "create_time": current_time,
            "update_time": current_time,
            "delete_time": None,
            "is_delete": False,
            "is_show": True
        })
        result = self.collection.insert_one(resume_data)
        return result.inserted_id

    def update_resume(self, resume_id, update_data):
        current_time = datetime.now()
        update_data["update_time"] = current_time
        result = self.collection.update_one({"_id": resume_id}, {"$set": update_data})
        return result.modified_count

    def delete_resume(self, resume_id):
        current_time = datetime.now()
        result = self.collection.update_one({"_id": resume_id},
                                            {"$set": {"delete_time": current_time, "is_delete": True}})
        return result.modified_count

    def get_resume(self, resume_id):
        return self.collection.find_one({"_id": resume_id})

    def list_resumes(self):
        return list(self.collection.find({"is_delete": False}))

    def list_deleted_resumes(self):
        return list(self.collection.find({"is_delete": True}))


# Example usage:
if __name__ == "__main__":
    manager = ResumeManager("your_db_name", "your_collection_name")

    # Create a new resume
    resume_data = {
        "basics": {},
        "skills": {},
        "work": [],
        "education": [],
        "activities": {},
        "volunteer": [],
        "awards": []
    }
    resume_id = manager.create_resume(resume_data)
    print("Created Resume ID:", resume_id)

    # Update the resume
    update_data = {"basics": {"name": "John Doe"}}
    manager.update_resume(resume_id, update_data)

    # Get the resume
    retrieved_resume = manager.get_resume(resume_id)
    print("Retrieved Resume:", retrieved_resume)

    # Delete the resume
    manager.delete_resume(resume_id)

    # List all active resumes and deleted resumes
    active_resumes = manager.list_resumes()
    deleted_resumes = manager.list_deleted_resumes()
    print("Active Resumes:", active_resumes)
    print("Deleted Resumes:", deleted_resumes)

    manager.close_connection()

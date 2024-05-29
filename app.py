import os
import uvicorn
from fastapi import FastAPI, Body, HTTPException
from pymongo import MongoClient
from typing import List, Dict, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from bson import ObjectId
from dotenv import load_dotenv


class notes_model(BaseModel):
    title : str
    content : str

class NoteInDB(notes_model):
    id: str = Field(alias="_id")
    createdAt: datetime
    updatedAt: datetime

def serialize_mongo_data(note) -> NoteInDB:
    return NoteInDB(
        _id=str(note["_id"]),
        title=note["title"],
        content=note["content"],
        createdAt=note["createdAt"],
        updatedAt=note["updatedAt"]
    )

class Notes_app:
    def __init__(self, mongo_uri : str, dbname : str, collection_name : str):
        self.client = MongoClient(mongo_uri)
        self.db = self.client[dbname]
        self.collection = self.db[collection_name]
        self.app = FastAPI()
        self.setup_routes()
        
    def setup_routes(self):
        @self.app.get('/api/notes', response_model=Dict[str, List[NoteInDB]])
        def index():
            return self.get_all_notes()
            
        @self.app.post('/api/notes', response_model=Dict[str, str])
        def create_note(note: notes_model = Body(...)):
            return self.create_new_note(note)

        @self.app.put('/api/notes/{note_id}', response_model=Dict[str, str])
        def update_note(note_id: str, note: notes_model = Body(...)):
            return self.update_existing_note(note_id, note)

        @self.app.delete('/api/notes/{note_id}', response_model=Dict[str, str])
        def delete_note(note_id: str):
            return self.delete_existing_note(note_id)


    def get_all_notes(self) -> Dict[str, List[NoteInDB]]:
        l = []
        res = self.collection.find({})
        for i in res:
            i['_id'] = str(i['_id'])
            l.append(i)
        
        # print(l)
        return {"notes" : l}
    
    def create_new_note(self, note : notes_model) -> Dict[str, str]:
        note_data = note.model_dump()
        note_data['createdAt'] = datetime.now(timezone.utc)
        note_data['updatedAt'] = datetime.now(timezone.utc)
        result = self.collection.insert_one(note_data)
        
        if result.inserted_id:
            return {"msg" : "Note created successfully" , "id" : str(result.inserted_id)}
        raise HTTPException(status_code=400, detail="Note creation failed")
    
    def update_existing_note(self, note_id : str, note : notes_model) -> Dict[str, str]:
        note_data = note.model_dump()
        # note_data['_id'] = str(note['_id'])
        note_data['updatedAt'] = datetime.now(timezone.utc)
        result = self.collection.update_one(
            {"_id" : ObjectId(note_id)},
            {"$set" : note_data}
        )
        
        if result.modified_count:
            return {"msg" : "Note has been updated successfully"}
        raise HTTPException(status_code=404, detail="Note not found")
    
    def delete_existing_note(self, note_id: str) -> Dict[str, str]:
        result = self.collection.delete_one({"_id" : ObjectId(note_id)})
        if result.deleted_count:
            return {"msg" : "note has been successfully Deleted!!"}
        raise HTTPException(status_code=404, detail= "Note not found!")
    
    def get_app(self):
        return self.app

load_dotenv()

notes_app = Notes_app(
    mongo_uri= os.getenv("MONGO_URI"),
    dbname= os.getenv("DATABASE_NAME"),
    collection_name= os.getenv("COLLECTION_NAME")
)

app = notes_app.get_app()

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8001, reload=True)
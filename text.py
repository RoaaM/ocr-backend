import os
from fastapi import FastAPI, Body, HTTPException, status
from fastapi.responses import Response, JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId
from typing import Optional, List
import motor.motor_asyncio


mongodb_url = 'mongodb+srv://employee:1234@atlascluster.v4i2hkf.mongodb.net/test'

app = FastAPI()
client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_url)
db = client.ocr


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class TextModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId = Field(None, alias="user_id")
    image_id: PyObjectId = Field(None, alias="image_id")
    text: str = Field(...)


    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "user_id": "25323216",
                "image_id": "213210203",
                "text": "any extracted text"
            }
        }


class UpdateTextModel(BaseModel):
    user_id: Optional[PyObjectId] = Field(None, alias="user_id")
    image_id: Optional[PyObjectId] = Field(None, alias="image_id")
    text: Optional[str]

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "_id": "321",
                "text": "any text",
            }
        }


@app.post("/text", response_description="Add new text")
async def create_text(text: TextModel = Body(...)):
    text = jsonable_encoder(text)
    new_text = await db["texts"].insert_one(text)
    created_text = await db["texts"].find_one({"_id": new_text.inserted_id})
    get_user = await db["users"].find_one({"_id": created_text["user_id"]})
    created_text['users'] = get_user
    get_image = await db["images"].find_one({"_id": created_text["image_id"]})
    created_text['images'] = get_image
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=created_text)


@app.get(
    "/texts", response_description="List all text", response_model=List[TextModel]
)
async def list_text():
    text = await db["texts"].find().to_list(1000)
    return text


@app.get(
    "/texts/{id}", response_description="Get a single text", response_model=TextModel
)
async def show_text(id: str):
    if (text := await db["texts"].find_one({"_id": id})) is not None:
        return text

    raise HTTPException(status_code=404, detail=f"text {id} not found")


@app.put("/texts/{id}", response_description="Update a text", response_model=TextModel)
async def update_text(id: str, text: UpdateTextModel = Body(...)):
    text = {k: v for k, v in text.dict().items() if v is not None}

    if len(text) >= 1:
        update_result = await db["texts"].update_one({"_id": id}, {"$set": text})

        if update_result.modified_count == 1:
            if (
                updated_text := await db["texts"].find_one({"_id": id})
            ) is not None:
                return updated_text

    if (existing_text := await db["texts"].find_one({"_id": id})) is not None:
        return existing_text

    raise HTTPException(status_code=404, detail=f"text {id} not found")


@app.delete("/texts/{id}", response_description="Delete a text")
async def delete_text(id: str):
    delete_result = await db["texts"].delete_one({"_id": id})

    if delete_result.deleted_count == 1:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"Text {id} not found")

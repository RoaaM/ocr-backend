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


class ImageModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId = Field(None, alias="user_id")
    path: str = Field(...)


    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "user_id": "2",
                "path": "c/image/file/image.png",
            }
        }


class UpdateImageModel(BaseModel):
    user_id: Optional[PyObjectId] = Field(None, alias="user_id")
    path: Optional[str]

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "_id": "321",
                "path": "c/image/file/image.png",
            }
        }


@app.post("/images", response_description="Add new image")
async def create_image(image: ImageModel = Body(...)):
    image = jsonable_encoder(image)
    new_image = await db["images"].insert_one(image)
    created_image = await db["images"].find_one({"_id": new_image.inserted_id})
    get_user = await db["users"].find_one({"_id": created_image["user_id"]})
    created_image['user'] = get_user
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=created_image)


@app.get(
    "/images", response_description="List all images", response_model=List[ImageModel]
)
async def list_images():
    images = await db["images"].find().to_list(1000)
    return images


@app.get(
    "/images/{id}", response_description="Get a single image", response_model=ImageModel
)
async def show_image(id: str):
    if (image := await db["images"].find_one({"_id": id})) is not None:
        return image

    raise HTTPException(status_code=404, detail=f"Student {id} not found")


@app.put("/images/{id}", response_description="Update a image", response_model=ImageModel)
async def update_image(id: str, image: UpdateImageModel = Body(...)):
    image = {k: v for k, v in image.dict().items() if v is not None}

    if len(image) >= 1:
        update_result = await db["images"].update_one({"_id": id}, {"$set": image})

        if update_result.modified_count == 1:
            if (
                updated_image := await db["images"].find_one({"_id": id})
            ) is not None:
                return updated_image

    if (existing_image := await db["images"].find_one({"_id": id})) is not None:
        return existing_image

    raise HTTPException(status_code=404, detail=f"Image {id} not found")


@app.delete("/images/{id}", response_description="Delete a image")
async def delete_image(id: str):
    delete_result = await db["images"].delete_one({"_id": id})

    if delete_result.deleted_count == 1:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"Image {id} not found")

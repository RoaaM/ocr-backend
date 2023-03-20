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


class UserModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str = Field(...)
    email: EmailStr = Field(...)
    password: str = Field(...)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "name": "Jane Doe",
                "email": "jdoe@example.com",
                "password": "123456",
            }
        }


class UpdateUserModel(BaseModel):
    name: Optional[str]
    email: Optional[EmailStr]
    password: Optional[str]

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "name": "Jane Doe",
                "email": "jdoe@example.com",
                "password": "123456",
            }
        }

@app.post("/users", response_description="Add new user", response_model=UserModel)
async def create_user(user: UserModel = Body(...)):
    # if len(user.password) > 12:
    #     raise ValueError("Password limit must be lower than 12 character")
    # salt = bcrypt.gensalt()
    # user.password = bcrypt.hashpw(user.password, salt)
    user = jsonable_encoder(user)
    new_user = await db["users"].insert_one(user)
    created_user = await db["users"].find_one({"_id": new_user.inserted_id})
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=created_user)


@app.get(
    "/users", response_description="List all users", response_model=List[UserModel]
)
async def list_users():
    users = await db["users"].find().to_list(1000)
    return users


@app.get(
    "/users/{id}", response_description="Get a single user", response_model=UserModel
)
async def show_user(id: str):
    if (user := await db["users"].find_one({"_id": id})) is not None:
        return user

    raise HTTPException(status_code=404, detail=f"Student {id} not found")


@app.put("/users/{id}", response_description="Update a user", response_model=UserModel)
async def update_user(id: str, user: UpdateUserModel = Body(...)):
    user = {k: v for k, v in user.dict().items() if v is not None}

    if len(user) >= 1:
        update_result = await db["users"].update_one({"_id": id}, {"$set": user})

        if update_result.modified_count == 1:
            if (
                updated_user := await db["users"].find_one({"_id": id})
            ) is not None:
                return updated_user

    if (existing_user := await db["users"].find_one({"_id": id})) is not None:
        return existing_user

    raise HTTPException(status_code=404, detail=f"User {id} not found")


@app.delete("/users/{id}", response_description="Delete a user")
async def delete_user(id: str):
    delete_result = await db["users"].delete_one({"_id": id})

    if delete_result.deleted_count == 1:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"User {id} not found")


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

    raise HTTPException(status_code=404, detail=f"image {id} not found")


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

@app.get(
    "/texts", response_description="List all text", response_model=List[TextModel]
)
async def list_text():
    text = await db["texts"].find().to_list(1000)
    return text



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



class GraphModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    text_id: PyObjectId = Field(None, alias="text_id")
    graph: str = Field(...)


    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "text_id": "2",
                "graph": "any graph",
            }
        }


class UpdateGraphModel(BaseModel):
    text_id: Optional[PyObjectId] = Field(None, alias="text_id")
    graph: Optional[str]

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "_id": "321",
                "graph": "first one",
            }
        }

@app.post("/graphs", response_description="Add new graph")
async def create_graph(graph: GraphModel = Body(...)):
    graph = jsonable_encoder(graph)
    new_graph = await db["graphs"].insert_one(graph)
    created_graph = await db["graphs"].find_one({"_id": new_graph.inserted_id})
    get_text = await db["texts"].find_one({"_id": created_graph["text_id"]})
    created_graph['texts'] = get_text
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=created_graph)


@app.get(
    "/graphs", response_description="List all graphs", response_model=List[GraphModel]
)
async def list_graphs():
    graphs = await db["graphs"].find().to_list(1000)
    return graphs


@app.get(
    "/graphs/{id}", response_description="Get a single graph", response_model=GraphModel
)
async def show_graph(id: str):
    if (graph := await db["graphs"].find_one({"_id": id})) is not None:
        return graph

    raise HTTPException(status_code=404, detail=f"graph {id} not found")


@app.put("/graphs/{id}", response_description="Update a graph", response_model=GraphModel)
async def update_graph(id: str, graph: UpdateGraphModel = Body(...)):
    graph = {k: v for k, v in graph.dict().items() if v is not None}

    if len(graph) >= 1:
        update_result = await db["graphs"].update_one({"_id": id}, {"$set": graph})

        if update_result.modified_count == 1:
            if (
                updated_graph := await db["graphs"].find_one({"_id": id})
            ) is not None:
                return updated_graph

    if (existing_graph := await db["graphs"].find_one({"_id": id})) is not None:
        return existing_graph

    raise HTTPException(status_code=404, detail=f"Graph {id} not found")


@app.delete("/graphs/{id}", response_description="Delete a graph")
async def delete_graph(id: str):
    delete_result = await db["graphs"].delete_one({"_id": id})

    if delete_result.deleted_count == 1:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"Graph{id} not found")



class SummaryModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    graph_id: PyObjectId = Field(None, alias="graph_id")
    summary: str = Field(...)


    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "graph_id": "2",
                "summary": "any summary",
            }
        }


class UpdateSummaryModel(BaseModel):
    graph_id: Optional[PyObjectId] = Field(None, alias="graph_id")
    summary: Optional[str]

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "_id": "321",
                "summary": "first one",
            }
        }

@app.post("/summaries", response_description="Add new summary")
async def create_summary(summary: SummaryModel = Body(...)):
    summary = jsonable_encoder(summary)
    new_summary = await db["summaries"].insert_one(summary)
    created_summary = await db["summaries"].find_one({"_id": new_summary.inserted_id})
    get_text = await db["graphs"].find_one({"_id": created_summary["graph_id"]})
    created_summary['graphs'] = get_text
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=created_summary)


@app.get(
    "/summaries", response_description="List all summaries", response_model=List[SummaryModel]
)
async def list_summaries():
    summaries = await db["summaries"].find().to_list(1000)
    return summaries


@app.get(
    "/summaries/{id}", response_description="Get a single summary", response_model=SummaryModel
)
async def show_summary(id: str):
    if (summary := await db["summaries"].find_one({"_id": id})) is not None:
        return summary

    raise HTTPException(status_code=404, detail=f"summary {id} not found")


@app.put("/summaries/{id}", response_description="Update a summary", response_model=SummaryModel)
async def update_summary(id: str, summary: UpdateSummaryModel = Body(...)):
    summary = {k: v for k, v in summary.dict().items() if v is not None}

    if len(summary) >= 1:
        update_result = await db["summaries"].update_one({"_id": id}, {"$set": summary})

        if update_result.modified_count == 1:
            if (
                updated_summary := await db["summaries"].find_one({"_id": id})
            ) is not None:
                return updated_summary

    if (existing_summary := await db["summaries"].find_one({"_id": id})) is not None:
        return existing_summary

    raise HTTPException(status_code=404, detail=f"Summary {id} not found")


@app.delete("/summaries/{id}", response_description="Delete a summary")
async def delete_summary(id: str):
    delete_result = await db["summaries"].delete_one({"_id": id})

    if delete_result.deleted_count == 1:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"Summary {id} not found")


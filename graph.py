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

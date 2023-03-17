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

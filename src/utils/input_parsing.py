from fastapi import Request, HTTPException, status
from typing import Type, TypeVar, Optional
from pydantic import BaseModel
from json import JSONDecodeError
import json

T = TypeVar("T", bound=BaseModel)

async def parse_request(request: Request, schema: Type[T]) -> T:
    content_type = request.headers.get("content-type", "").lower()
    
    data = {}
    
    if "application/json" in content_type:
        try:
            data = await request.json()
        except JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON")
    elif "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        data = {k: v for k, v in form.items()}
    else:
        # Try JSON fallback
        try:
            data = await request.json()
        except:
            pass
            
    if not data:
         # Try form fallback
        try:
            form = await request.form()
            data = {k: v for k, v in form.items()}
        except:
            pass

    # If results came in as a JSON string in form-data, parse it
    if isinstance(data, dict) and 'results' in data and isinstance(data['results'], str):
        try:
            data['results'] = json.loads(data['results'])
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid results JSON: {str(e)}")

    try:
        # Use pydantic model validation (v2)
        return schema.model_validate(data)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

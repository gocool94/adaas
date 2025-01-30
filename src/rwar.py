from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import snowflake.connector
import pandas as pd
import uvicorn
import logging

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Replace with your React app's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Snowflake connection
def get_snowflake_session():
    return snowflake.connector.connect(
        user="gokulkalivarathanmm",
        password="Spinfocity@6amazon",
        account="gfb50954",
        warehouse="COMPUTE_WH",
        database="KIPI_KIPI_PRIMARY_ADAAS_SNOWFLAKE_SECURE_SHARE",
        schema="DATA_SCIENCE",
    )



# Constants
CHAT_MEMORY = 20
DOMAINS = [
    "KIPI_KIPI_PRIMARY_ADAAS_SNOWFLAKE_SECURE_SHARE.DATA_SCIENCE.DS_BUCKET_DATA",
    "KIPI_KIPI_PRIMARY_ADAAS_SNOWFLAKE_SECURE_SHARE.DATA_SCIENCE.DE_BUCKET_DATA",
    "KIPI_KIPI_PRIMARY_ADAAS_SNOWFLAKE_SECURE_SHARE.DATA_SCIENCE.DG_BUCKET_DATA",
    "KIPI_KIPI_PRIMARY_ADAAS_SNOWFLAKE_SECURE_SHARE.DATA_SCIENCE.BI_BUCKET_DATA",
    "KIPI_KIPI_PRIMARY_ADAAS_SNOWFLAKE_SECURE_SHARE.DATA_SCIENCE.PM_BUCKET_DATA",
]

# Pydantic model for request body
class QueryRequest(BaseModel):
    chat: str
    model: str
    file: Optional[str] = None

# Summarize function
def summarize(chat: str, model: str) -> str:
    # Replace this with your actual summarization logic
    return f"Summary of: {chat}"

# Find similar document
def find_similar_doc(text: str, doc_table: str, session) -> dict:
    try:
        query = f"""
            SELECT JSON_OBJECT,
                   MATURITY_LEVEL,
                   VECTOR_COSINE_SIMILARITY(embedding, SNOWFLAKE.CORTEX.EMBED_TEXT_768('e5-base-v2', '{text.replace("'", "''")}')) as dist
            FROM {doc_table}
            ORDER BY dist DESC
            LIMIT 1
        """
        doc = session.cursor().execute(query).fetch_pandas_all()
        return doc
    except Exception as e:
        logging.error(f"Error finding similar document: {e}")
        raise

# Get all maturity levels
def get_all_maturity_levels(doc_table: str, session) -> List[str]:
    try:
        query = f"SELECT DISTINCT MATURITY_LEVEL FROM {doc_table} ORDER BY MATURITY_LEVEL ASC"
        result = session.cursor().execute(query).fetch_pandas_all()
        return result["MATURITY_LEVEL"].tolist()
    except Exception as e:
        logging.error(f"Error fetching maturity levels: {e}")
        raise

# Compute next bucket
def compute_next_bucket(current_bucket: str, maturity_levels: List[str]) -> str:
    try:
        index = maturity_levels.index(current_bucket)
        if index < len(maturity_levels) - 1:
            return maturity_levels[index + 1]
        else:
            return "No next bucket available"
    except ValueError:
        return "Current bucket not found in maturity levels"

# Get prompt
def get_prompt(chat: str, context: str, doc_table: str, session) -> str:
    try:
        query = f"SELECT JSON_OBJECT, MATURITY_LEVEL FROM {doc_table}"
        doc = session.cursor().execute(query).fetch_pandas_all()
        default_level = doc["MATURITY_LEVEL"][0]
        prompt = f"""
            Answer this new customer question sent to our support agent. Use the
            provided context taken from the most relevant previous support chat logs with other customers.
            Be concise and only answer the latest question. Give some description about next
            level to be achieved according to context also along with current bucket in which it falls.
            If the context does not indicate the current maturity level,
            assume the customer is at the first level: '{default_level}'.
            Also, highlight the Bucket levels in the response and bold the text for bucket names.
            The question is in the chat.
            Chat: <chat> {chat} </chat>.
            Context: <context> {context} </context>.
        """
        return prompt
    except Exception as e:
        logging.error(f"Error constructing prompt: {e}")
        raise

# LLM completion
def complete(model: str, prompt: str) -> str:
    # Replace this with your actual LLM completion logic
    return f"Response from {model}: {prompt}"

# Endpoint to handle chat
@app.post("/query")
async def query(request: QueryRequest):
    session = get_snowflake_session()
    chat = request.chat
    model = request.model
    file_content = request.file

    try:
        responses = []
        for doc_table in DOMAINS:
            # Get context
            context = find_similar_doc(chat, doc_table, session)
            current_bucket = context["MATURITY_LEVEL"].iloc[0]

            # Get all maturity levels
            maturity_levels = get_all_maturity_levels(doc_table, session)

            # Compute next bucket
            next_bucket = compute_next_bucket(current_bucket, maturity_levels)

            # Construct prompt
            prompt = get_prompt(chat, context, doc_table, session)

            # Get response from LLM
            response = complete(model, prompt)

            responses.append({
                "answer": response,
                "context": context,
                "current_bucket": current_bucket,
                "next_bucket": next_bucket,
            })
        return responses
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

# Endpoint to handle file upload
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        content = await file.read()
        return {"filename": file.filename, "content": content.decode("utf-8")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Run the FastAPI app
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
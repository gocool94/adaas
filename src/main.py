from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import snowflake.connector
import logging

# Initialize the app
app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# CORS Middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React app URL
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Snowflake credentials
snowflake_credentials = {
    "account": "gfb50954",
    "user": "gokulkalivarathanmm",
    "password": "Spinfocity@6amazon",
    "warehouse": "COMPUTE_WH",
    "database": "KIPI_KIPI_PRIMARY_ADAAS_SNOWFLAKE_SECURE_SHARE",
    "schema": "DATA_SCIENCE",
}

# Domains
domains = [
    "KIPI_KIPI_PRIMARY_ADAAS_SNOWFLAKE_SECURE_SHARE.DATA_SCIENCE.DS_BUCKET_DATA",
    "KIPI_KIPI_PRIMARY_ADAAS_SNOWFLAKE_SECURE_SHARE.DATA_SCIENCE.DE_BUCKET_DATA",
    "KIPI_KIPI_PRIMARY_ADAAS_SNOWFLAKE_SECURE_SHARE.DATA_SCIENCE.DG_BUCKET_DATA",
    "KIPI_KIPI_PRIMARY_ADAAS_SNOWFLAKE_SECURE_SHARE.DATA_SCIENCE.BI_BUCKET_DATA",
    "KIPI_KIPI_PRIMARY_ADAAS_SNOWFLAKE_SECURE_SHARE.DATA_SCIENCE.PM_BUCKET_DATA",
]

# Models
class QueryRequest(BaseModel):
    chat: str
    model: str
    domains: Optional[List[str]] = None  # Override default domains if needed

class QueryResponse(BaseModel):
    answer: Dict  # Changed from str to Dict to accommodate structured responses
    context: str
    current_bucket: str
    next_bucket: str

# Snowflake connection
def get_snowflake_connection():
    """Establish a connection to the Snowflake database."""
    try:
        logging.info("Connecting to Snowflake...")
        connection = snowflake.connector.connect(**snowflake_credentials)
        logging.info("Connected to Snowflake.")
        return connection
    except Exception as e:
        logging.error(f"Error connecting to Snowflake: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect to Snowflake")

# Helper: Find similar document
def find_similar_doc(connection, text: str, doc_table: str) -> Dict:
    """Find the most similar document in the specified table."""
    try:
        cursor = connection.cursor()
        query = f"""
            SELECT JSON_OBJECT, MATURITY_LEVEL,
                VECTOR_COSINE_SIMILARITY(
                    embedding,
                    SNOWFLAKE.CORTEX.EMBED_TEXT_768('e5-base-v2', '{text.replace("'", "''")}')
                ) AS dist
            FROM {doc_table}
            ORDER BY dist DESC
            LIMIT 1
        """
        cursor.execute(query)
        result = cursor.fetchone()
        return {
            "json_object": result[0],
            "maturity_level": result[1],
        }
    except Exception as e:
        logging.error(f"Error finding similar document: {e}")
        raise HTTPException(status_code=500, detail="Failed to find similar document")

# Helper: Generate a structured response
def generate_response(context: str, current_bucket: str, next_bucket: str) -> Dict:
    """
    Dynamically parse the response context into a structured format.
    """
    import re

    description_match = re.search(r'"DESCRIPTION":"(.*?)"', context, re.DOTALL)
    level_match = re.search(r'"MATURITY_LEVEL":"(.*?)"', context)

    description = description_match.group(1).strip() if description_match else "No description available."
    maturity_level = level_match.group(1).strip() if level_match else "Unknown"

    # Split the description into bullet points
    details = [line.strip() for line in description.split("\n") if line.strip()]

    return {
        "current_bucket": {
            "name": maturity_level,
            "description": "Most Mature",
            "details": details,
        },
        "next_bucket": {
            "name": next_bucket,
            "description": "Future Level of Maturity",
            "focus": "Achieving scalability, fully automated deployment pipelines, and seamless integration for all data science workflows."
        }
    }

@app.post("/query", response_model=List[QueryResponse])
async def query_endpoint(query_request: QueryRequest):
    """
    Handle POST requests to the /query endpoint.
    Iterate through all domains and return detailed responses for each.
    """
    chat = query_request.chat
    model = query_request.model
    selected_domains = query_request.domains or domains

    try:
        connection = get_snowflake_connection()
        responses = []

        # Iterate through all domains
        for doc_table in selected_domains:
            try:
                # Find the most relevant document
                doc_data = find_similar_doc(connection, chat, doc_table)
                context = doc_data["json_object"]
                current_bucket = doc_data["maturity_level"]

                # Determine the next maturity bucket
                cursor = connection.cursor()
                query = f"""
                    SELECT DISTINCT MATURITY_LEVEL
                    FROM {doc_table}
                    ORDER BY MATURITY_LEVEL
                """
                cursor.execute(query)
                maturity_levels = [row[0] for row in cursor.fetchall()]

                # Find the next bucket
                next_bucket_index = maturity_levels.index(current_bucket) + 1
                next_bucket = (
                    maturity_levels[next_bucket_index]
                    if next_bucket_index < len(maturity_levels)
                    else "Does not exist"
                )

                # Generate a structured response for this domain
                structured_response = generate_response(context, current_bucket, next_bucket)
                responses.append(
                    QueryResponse(
                        answer=structured_response,
                        context=context,
                        current_bucket=current_bucket,
                        next_bucket=next_bucket,
                    )
                )
                logging.info(f"Response ******************")
                logging.info(f"Response to frontend: {responses}")


            except Exception as e:
                logging.warning(f"Error processing domain {doc_table}: {e}")
                continue  # Skip this domain and process the next

        if not responses:
            raise HTTPException(status_code=404, detail="No relevant documents found in any domain.")

        return responses

    except Exception as e:
        logging.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

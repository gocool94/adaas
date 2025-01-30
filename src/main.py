from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import snowflake.connector
import logging
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI app
app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ✅ Allow frontend
    allow_credentials=True,
    allow_methods=["*"],  # ✅ Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],
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

# Define domains and maturity level mapping
domains = [
    "KIPI_KIPI_PRIMARY_ADAAS_SNOWFLAKE_SECURE_SHARE.DATA_SCIENCE.DS_BUCKET_DATA",
    "KIPI_KIPI_PRIMARY_ADAAS_SNOWFLAKE_SECURE_SHARE.DATA_SCIENCE.DE_BUCKET_DATA",
    "KIPI_KIPI_PRIMARY_ADAAS_SNOWFLAKE_SECURE_SHARE.DATA_SCIENCE.DG_BUCKET_DATA",
    "KIPI_KIPI_PRIMARY_ADAAS_SNOWFLAKE_SECURE_SHARE.DATA_SCIENCE.BI_BUCKET_DATA",
    "KIPI_KIPI_PRIMARY_ADAAS_SNOWFLAKE_SECURE_SHARE.DATA_SCIENCE.PM_BUCKET_DATA",
]

maturity_mapping = {
    "DS": "Data Science",
    "DE": "Data Engineering",
    "DG": "Data Governance",
    "BI": "Business Intelligence",
    "PM": "Project Management",
}

# Request Model
class ChatRequest(BaseModel):
    chat: str

# Function to connect to Snowflake
def get_snowflake_connection():
    logger.info("Connecting to Snowflake...")
    try:
        conn = snowflake.connector.connect(
            user=snowflake_credentials["user"],
            password=snowflake_credentials["password"],
            account=snowflake_credentials["account"],
            warehouse=snowflake_credentials["warehouse"],
            database=snowflake_credentials["database"],
            schema=snowflake_credentials["schema"]
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(status_code=500, detail="Database connection error")

# Summarize chat input
def summarize(chat: str, model: str):
    logger.info("Summarizing chat input...")
    query = f"""
        SELECT SNOWFLAKE.CORTEX.COMPLETE('{model}', 
        'Provide the most recent question with essential context from this support chat: {chat.replace("'", "''")}')
    """
    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        summary = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return summary.replace("'", "")
    except Exception as e:
        logger.error(f"Error summarizing chat: {e}")
        raise HTTPException(status_code=500, detail="Error summarizing chat")

# Retrieve relevant document and next maturity level
def find_similar_doc(text: str, doc_table: str):
    logger.info(f"Retrieving most relevant document for: {doc_table}...")

    query = f"""
    SELECT JSON_OBJECT, MATURITY_LEVEL, 
           VECTOR_COSINE_SIMILARITY(embedding, SNOWFLAKE.CORTEX.EMBED_TEXT_768('e5-base-v2', '{text.replace("'", "''")}')) as dist
    FROM {doc_table}
    ORDER BY dist DESC
    LIMIT 1
    """

    next_level_query = f"""
    SELECT JSON_OBJECT, MATURITY_LEVEL FROM {doc_table}
    ORDER BY MATURITY_LEVEL
    """

    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()

        # Get current maturity level
        cursor.execute(query)
        doc = cursor.fetchone()

        # Get all maturity levels sorted
        cursor.execute(next_level_query)
        maturity_docs = cursor.fetchall()

        cursor.close()
        conn.close()

        if doc:
            current_maturity = doc[1]
            next_maturity = "Does not exist"

            for i, (json_obj, maturity_level) in enumerate(maturity_docs):
                if maturity_level == current_maturity and i + 1 < len(maturity_docs):
                    next_maturity = maturity_docs[i + 1][1]
                    break

            return {
                "json_object": doc[0],
                "maturity_level": current_maturity,
                "next_maturity_level": next_maturity,
            }
        return None
    except Exception as e:
        logger.error(f"Error retrieving similar document: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving similar document")

# Construct AI prompt
def construct_prompt(chat: str, context: str, current_level: str, next_level: str):
    prompt = f"""
    Answer this new customer question sent to our support agent. Use the provided context taken from previous support chat logs. 
    Be concise and only answer the latest question.

    - **Current Maturity Level**: {current_level}
    - **Next Maturity Level**: {next_level}

    Question: {chat}
    Context: {context}
    """
    return prompt.replace("'", "")

# Generate AI response
def get_response(prompt: str, model: str):
    logger.info("Generating AI response...")
    query = f"""
        SELECT SNOWFLAKE.CORTEX.COMPLETE('{model}', '{prompt.replace("'", "''")}')
    """
    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        response = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return response
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        raise HTTPException(status_code=500, detail="Error generating response")

# FastAPI endpoint to handle chat requests
@app.post("/chat")
def chat_with_bot(request: ChatRequest):
    logger.info(f"Received chat request: {request.chat}")
    model = "mistral-large"

    # Step 1: Summarize chat
    chat_summary = summarize(request.chat, model)

    # Step 2: Process all domains
    responses = []
    for doc_table in domains:
        context = find_similar_doc(chat_summary, doc_table)
        
        if context:
            domain_code = doc_table.split(".")[-1][:2]
            domain_name = maturity_mapping.get(domain_code, "Unknown")

            prompt = construct_prompt(
                request.chat, 
                context["json_object"], 
                context["maturity_level"], 
                context["next_maturity_level"]
            )
            response = get_response(prompt, model)

            responses.append({
                "domain": domain_name,
                "maturity_level": context["maturity_level"],
                "next_maturity_level": context["next_maturity_level"],
                "response": response
            })
            logger.info(responses)

    if not responses:
        raise HTTPException(status_code=404, detail="No relevant context found.")
    
    return responses

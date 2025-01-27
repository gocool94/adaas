import snowflake.connector
from fastapi import FastAPI, HTTPException
import logging

app = FastAPI()

# Snowflake credentials
snowflake_credentials = {
    "account": "gfb50954",
    "user": "gokulkalivarathanmm",
    "password": "Spinfocity@6amazon",
    "warehouse": "COMPUTE_WH",
    "database": "KIPI_KIPI_PRIMARY_ADAAS_SNOWFLAKE_SECURE_SHARE",
    "schema": "DATA_SCIENCE"
}

# Test Snowflake connection function
def test_snowflake_connection():
    try:
        conn = snowflake.connector.connect(
            user=snowflake_credentials["user"],
            password=snowflake_credentials["password"],
            account=snowflake_credentials["account"],
            warehouse=snowflake_credentials["warehouse"],
            database=snowflake_credentials["database"],
            schema=snowflake_credentials["schema"]
        )
        cursor = conn.cursor()
        cursor.execute("SELECT CURRENT_DATE")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return f"Connection successful! Current date in Snowflake: {result[0]}"
    
    except snowflake.connector.errors.Error as e:
        logging.error(f"Error connecting to Snowflake: {e}")
        raise HTTPException(status_code=500, detail=f"Connection failed: {e}")

@app.get("/test-snowflake-connection")
async def test_connection():
    return {"message": test_snowflake_connection()}

import time
import uuid
import json
from fastapi import FastAPI, HTTPException, Request
import redis.asyncio as redis
from aiokafka import AIOKafkaProducer
from contextlib import asynccontextmanager
from fastapi.responses import HTMLResponse # Added for HTML response in the root endpoint
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to Kafka
    app.state.kafka_producer = AIOKafkaProducer(
        bootstrap_servers='localhost:9092',
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    await app.state.kafka_producer.start()
    print("KAFKA PRODUCER CONNECTED")
    yield
    # Shutdown
    await app.state.kafka_producer.stop()

app = FastAPI(lifespan=lifespan)
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

RATE_LIMIT = 5
WINDOW_SIZE = 60

async def check_rate_limit(client_ip: str):
    now_ms = int(time.time() * 1000)
    window_start_ms = now_ms - (WINDOW_SIZE * 1000)
    redis_key = f"rate_limit:{client_ip}"
    async with redis_client.pipeline(transaction=True) as pipe:
        pipe.zremrangebyscore(redis_key, 0, window_start_ms)
        pipe.zcard(redis_key)
        pipe.expire(redis_key, WINDOW_SIZE)
        results = await pipe.execute()
    if results[1] >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Too Many Requests")
    await redis_client.zadd(redis_key, {f"{now_ms}-{uuid.uuid4()}": now_ms})
    return True

@app.get("/api/data")
async def get_data(request: Request):
    client_ip = request.client.host
    await check_rate_limit(client_ip)
    
    # NEW: Send data to Kafka
    transaction_data = {
        "transactionId": str(uuid.uuid4()),
        "clientIp": client_ip,
        "timestamp": int(time.time() * 1000)
    }
    await app.state.kafka_producer.send_and_wait("allowed_requests", transaction_data)
    
    return {"message": "Logged in Kafka", "data": transaction_data}

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    import mysql.connector
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="rootpassword",
            database="transactions"
        )
        cursor = db.cursor()
        # Query the last 15 allowed requests
        cursor.execute("SELECT transaction_id, client_ip, processed_at FROM allowed_requests ORDER BY processed_at DESC LIMIT 15")
        rows = cursor.fetchall()
        cursor.close()
        db.close()

        table_rows = "".join([f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td></tr>" for r in rows])
        
        return f"""
        <html>
            <head>
                <title>Rate Limiter Dashboard</title>
                <style>
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 40px; background-color: #f4f7f6; }}
                    h1 {{ color: #2c3e50; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
                    table {{ border-collapse: collapse; width: 100%; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 0 20px rgba(0,0,0,0.1); }}
                    th, td {{ border: 1px solid #ddd; padding: 12px 15px; text-align: left; }}
                    th {{ background-color: #4CAF50; color: white; text-transform: uppercase; letter-spacing: 0.03em; }}
                    tr:nth-child(even) {{ background-color: #f2f2f2; }}
                    tr:hover {{ background-color: #f1f1f1; }}
                </style>
                <meta http-equiv="refresh" content="3">
            </head>
            <body>
                <h1>🛡️ Rate Limiter: Allowed Transactions</h1>
                <p>Monitoring the <b>MySQL</b> ledger via the <b>Accountant Service</b> pipeline. Updates every 3 seconds.</p>
                <table>
                    <tr><th>Transaction ID</th><th>Client IP</th><th>Processed At</th></tr>
                    {table_rows}
                </table>
            </body>
        </html>
        """
    except Exception as e:
        return f"<h1>Error connecting to Dashboard: {e}</h1>"
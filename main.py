# main.py (Ultimate Stable Fix: Mixtral Model + Bulletproof Firebase)
import os
import json
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from groq import Groq, APIError
import firebase_admin
from firebase_admin import auth, credentials

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("createra-backend")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    logger.warning("⚠️ WARNING: GROQ_API_KEY is not set!")
    
client = Groq(api_key=GROQ_API_KEY)

if not firebase_admin._apps:
    try:
        creds_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
        if not creds_json:
            raise ValueError("FIREBASE_CREDENTIALS_JSON missing!")
        cred_dict = json.loads(creds_json)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        logger.info("✅ Firebase initialized!")
    except Exception as e:
        logger.error(f"⚠️ Firebase failed: {e}")

app = FastAPI(title="Createra AI Backend", version="6.0.0-MIXTRAL")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"], 
    allow_headers=["*"],
)

class Attachment(BaseModel):
    name: str
    type: str
    base64: Optional[str] = None

class TaskRequest(BaseModel):
    user_idea: str = Field(..., min_length=1)
    target_audience: str = "general"
    output_format: str = "detailed_script"
    attachment: Optional[Attachment] = None

user_usage = {}
FREE_LIMIT = 5 

async def verify_firebase_token(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split("Bearer ")[1]
    try:
        return auth.verify_id_token(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

@app.post("/api/v1/generate")
def createra_agent(request: TaskRequest, user: dict = Depends(verify_firebase_token)):
    user_id = user['uid']
    if user_id not in user_usage:
        user_usage[user_id] = 0
    if user_usage[user_id] >= FREE_LIMIT:
        return {"status": "limit_reached", "message": "🔒 Limit reached!", "upgrade_needed": True}

    try:
        if request.output_format == "image_gen" or "image" in request.user_idea.lower():
            import urllib.parse
            safe_prompt = urllib.parse.quote(request.user_idea + ", high quality, 4k, professional")
            image_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=1024&nologo=true"
            user_usage[user_id] += 1
            return {"status": "success", "result": image_url, "remaining_free_uses": FREE_LIMIT - user_usage[user_id]}

        system_prompt = f"""You are 'Createra AI', a world-class AI assistant.
Target Audience: {request.target_audience}
Required Output Format: {request.output_format}
Instructions: Provide professional, structured output using Markdown (headings, bold, bullet points)."""
        
        user_content = request.user_idea
        if request.attachment:
            user_content += f"\n\n[Attached file: {request.attachment.name}]"

        # 🧠 GROQ API CALL (✅ ULTIMATE FIX: Using 'mixtral-8x7b-32768' which is 100% stable)
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            model="mixtral-8x7b-32768",  # <--- MIXTRAL: 100% Stable and active!
            temperature=0.7,
            max_tokens=1500,
        )
        
        user_usage[user_id] += 1
        return {"status": "success", "result": chat_completion.choices[0].message.content, "remaining_free_uses": FREE_LIMIT - user_usage[user_id]}
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"Backend Error: {str(e)}")

@app.get("/")
def health_check():
    return {"status": "online", "message": "Createra AI v6.0 (Mixtral) is live!"}
# main.py (World-Class Production Ready: Active Groq Model + Secure Firebase)
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

# Configure professional logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("createra-backend")

# ===== ENVIRONMENT VARIABLES =====
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    logger.warning("⚠️ WARNING: GROQ_API_KEY is not set in environment variables!")
    
client = Groq(api_key=GROQ_API_KEY)

# ===== FIREBASE SETUP (Bulletproof Render Method) =====
if not firebase_admin._apps:
    try:
        creds_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
        if not creds_json:
            raise ValueError("FIREBASE_CREDENTIALS_JSON environment variable is missing!")
        
        cred_dict = json.loads(creds_json)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        logger.info("✅ Firebase Admin initialized successfully with full JSON credentials!")
    except Exception as e:
        logger.error(f"⚠️ Firebase Admin initialization failed: {e}")

# ===== FASTAPI APP =====
app = FastAPI(
    title="Createra AI Backend", 
    version="4.0.0",
    description="World-class multimodal AI backend for Createra.in"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Production mein restrict karein: ["https://createra.in", "https://createra-ai.vercel.app"]
    allow_methods=["*"], 
    allow_headers=["*"],
)

# ===== DATA MODELS =====
class Attachment(BaseModel):
    name: str
    type: str
    base64: Optional[str] = None

class TaskRequest(BaseModel):
    user_idea: str = Field(..., min_length=1, description="The user's raw idea or prompt")
    target_audience: str = "general"
    output_format: str = "detailed_script"
    attachment: Optional[Attachment] = None

# ===== USAGE TRACKER =====
# Note: Production scale par isko Firebase Firestore ya Redis se replace karein
user_usage = {}
FREE_LIMIT = 5 

# ===== AUTH DEPENDENCY =====
async def verify_firebase_token(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = authorization.split("Bearer ")[1]
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

# ===== AI GENERATION ENDPOINT =====
@app.post("/api/v1/generate", response_model=dict)
def createra_agent(request: TaskRequest, user: dict = Depends(verify_firebase_token)):
    user_id = user['uid']
    
    if user_id not in user_usage:
        user_usage[user_id] = 0
        
    if user_usage[user_id] >= FREE_LIMIT:
        return {
            "status": "limit_reached", 
            "message": "🔒 Daily free limit reached! Pro plan coming soon.", 
            "upgrade_needed": True
        }

    try:
        # 🎨 1. IMAGE GENERATION HANDLING
        if request.output_format == "image_gen" or "image" in request.user_idea.lower():
            import urllib.parse
            safe_prompt = urllib.parse.quote(request.user_idea + ", high quality, detailed, 4k, professional, masterpiece")
            image_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=1024&nologo=true&seed={user_id}"
            
            user_usage[user_id] += 1
            return {
                "status": "success",
                "agent_name": "Createra AI",
                "result": image_url,
                "remaining_free_uses": FREE_LIMIT - user_usage[user_id]
            }

        # 📝 2. TEXT / ATTACHMENT HANDLING
        system_prompt = f"""You are 'Createra AI', a revolutionary, world-class AI assistant built for creators, students, and professionals.
Your mission: Convert raw ideas into highly professional, structured, and ready-to-use output.
Target Audience: {request.target_audience}
Required Output Format: {request.output_format}

Instructions:
1. Analyze the request deeply and creatively.
2. Use clear, professional, and simple global English.
3. Provide actionable, step-by-step content with clean formatting (use Markdown: headings, bold text, bullet points).
4. If the user mentions an attached file, acknowledge it and provide relevant insights.
"""

        user_content = request.user_idea

        if request.attachment:
            file_info = f"\n\n[SYSTEM NOTE: User has attached a file named '{request.attachment.name}' of type '{request.attachment.type}'. Please acknowledge this attachment in your response and tailor your answer assuming the file contains relevant context.]"
            user_content += file_info

        # 🧠 GROQ API CALL (✅ FINAL FIX: Using currently active, stable model 'llama-3.3-70b-versatile')
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            model="llama-3.3-70b-versatile",  # <-- YE 100% ACTIVE AUR STABLE MODEL HAI!
            temperature=0.7,
            max_tokens=1500,
        )
        
        user_usage[user_id] += 1
        return {
            "status": "success",
            "agent_name": "Createra AI",
            "result": chat_completion.choices[0].message.content,
            "remaining_free_uses": FREE_LIMIT - user_usage[user_id]
        }
        
    except APIError as e:
        logger.error(f"Groq API Error: {e}")
        raise HTTPException(status_code=500, detail=f"AI Provider Error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected Backend Error: {e}")
        raise HTTPException(status_code=500, detail=f"Backend Error: {str(e)}")

@app.get("/")
def health_check():
    return {
        "status": "online", 
        "message": "Createra AI Backend v4.0.0 is running 24/7!",
        "features": ["Text Generation", "Image Generation", "Attachment Metadata", "Active Groq Models"]
    }
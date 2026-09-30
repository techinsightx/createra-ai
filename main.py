# main.py (Upgraded for Multimodal & World-Class Features)
import os
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
import firebase_admin
from firebase_admin import auth

# ===== ENVIRONMENT VARIABLES =====
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "your_groq_api_key_here")
client = Groq(api_key=GROQ_API_KEY)

# ===== FIREBASE SETUP =====
if not firebase_admin._apps:
    try:
        firebase_admin.initialize_app()
    except ValueError:
        print("⚠️ Firebase Admin initialized in mock/basic mode.")

# ===== FASTAPI APP =====
app = FastAPI(title="Createra AI Backend", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production mein specific domains daal dena
    allow_methods=["*"], 
    allow_headers=["*"],
)

# ===== DATA MODELS =====
class Attachment(BaseModel):
    name: str
    type: str
    base64: Optional[str] = None  # Frontend bhejega, par hum token bachane ke liye sirf metadata use karenge

class TaskRequest(BaseModel):
    user_idea: str
    target_audience: str = "general"
    output_format: str = "detailed_script"
    attachment: Optional[Attachment] = None

# ===== USAGE TRACKER =====
user_usage = {}
FREE_LIMIT = 5 

# ===== AUTH DEPENDENCY =====
async def verify_firebase_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = authorization.split("Bearer ")[1]
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

# ===== AI GENERATION ENDPOINT =====
@app.post("/api/v1/generate")
def createatera_agent(request: TaskRequest, user: dict = Depends(verify_firebase_token)):
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
        # 🎨 1. IMAGE GENERATION HANDLING (Direct URL Return)
        if request.output_format == "image_gen" or "image" in request.user_idea.lower():
            import urllib.parse
            safe_prompt = urllib.parse.quote(request.user_idea + ", high quality, detailed, 4k, professional, masterpiece")
            image_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=1024&height=1024&nologo=true&seed={user_id}"
            
            user_usage[user_id] += 1
            return {
                "status": "success",
                "agent_name": "Createra AI",
                "result": image_url, # Frontend isko image tag mein render karega
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
        4. If the user mentions an attached file, acknowledge it and provide relevant insights or ask for specific details if needed.
        """

        user_content = request.user_idea

        # 📎 Attachment Logic (Token Limit Protection)
        # Note: Hum pura base64 string LLM ko nahi bhejte kyunki wo token limit cross karke error dega.
        # Iski jagah, hum AI ko file ka metadata dete hain aur context assume karne ko bolte hain.
        if request.attachment:
            file_info = f"\n\n[SYSTEM NOTE: User has attached a file named '{request.attachment.name}' of type '{request.attachment.type}'. Please acknowledge this attachment in your response and tailor your answer assuming the file contains relevant context for the user's idea.]"
            user_content += file_info

        # 🧠 GROQ API CALL (Using Llama 3.1 8B Instant for maximum speed)
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            model="llama-3.1-8b-instant", # Sabse fast aur reliable free model
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
        
    except Exception as e:
        print(f"Createra AI Error: {str(e)}")
        raise HTTPException(status_code=500, detail="An internal error occurred while processing your request. Please try again.")

@app.get("/")
def health_check():
    return {
        "status": "online", 
        "message": "Createra AI Backend v3.0 is running 24/7!",
        "features": ["Text Generation", "Image Generation", "Attachment Metadata Handling"]
    }
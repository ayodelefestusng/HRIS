# from cv2 import log
# from cv2 import log
from dotenv import load_dotenv
load_dotenv()
from deep_translator import GoogleTranslator
from pydantic import BaseModel, Field
import os
import sys
import types
import logging
from sqlalchemy.orm import Session
# yyy
import os
import json
import logging
import traceback
from typing import List, Optional, Any
# import pandas as pd
# import numpy as np
import time
# from cv2 import log
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from langchain_community.utilities import SQLDatabase

from logging.handlers import RotatingFileHandler
import re
import hashlib
import functools
from typing import Dict, Union

import os 
from langchain_google_genai import ChatGoogleGenerativeAI


from chat_bot import process_message, initialize_vector_store, llm, get_llm_instance
from database import init_db, SessionLocal, Tenant, Conversation, Message, Prompt, LLM
from models_utils import (FinalResponse,json_to_dataframe,detect_high_risk_changes,
calculate_comparison_table,get_gemini_insights,GrossPayReconciliation,SuspiciousAnalysisItem,
NewEmployeeItem,ContinuingEmployee,ChatRequest,OnboardRequest,
UpdateRequest,ollama_insights,StateOutput,PayrollComparisonInsights,get_comprehensive_analysis,
PromptRequest, HelloAIRequest, LLMUpdate,SummarizeRequest,SentenceAnalyzeRequest,SummarizeResponse
)
from ollama_service import OllamaService

# Use print for immediate console visibility during restart
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
print(f"DEBUG STARTUP: Key found={bool(api_key)}")
if api_key:
    os.environ["GEMINI_API_KEY"] = api_key
    os.environ["GOOGLE_API_KEY"] = api_key
    print(f"DEBUG STARTUP: Synchronized GEMINI_API_KEY and GOOGLE_API_KEY in os.environ")




@app.post("/onboard/", 
          summary="Onboard New Tenant", 
          description="Registers a new tenant with specific configuration and re-indexes the knowledge base.")
async def onboard_endpoint(request: OnboardRequest):
    db = SessionLocal()
    try:
        logger.info(f"Onboard View Called ")
        # --- Trigger Global LLM Check/Creation ---
        get_or_create_global_llm()
        
        # --- Handle Default Prompt Initialization ---
        requested_prompt_type = request.prompt_type or "standard"
        default_prompt_name = os.getenv("name", "standard")
        
        # Use requested prompt_type to fetch Prompt
        logger.info(f"Checking for prompt with name: {requested_prompt_type}")
        prompt_record = db.query(Prompt).filter(Prompt.name == requested_prompt_type).first()

        # If not found, try to fallback to "standard" or whatever is in ENV
        if not prompt_record and requested_prompt_type != default_prompt_name:
            logger.info(f"Prompt '{requested_prompt_type}' not found. Falling back to '{default_prompt_name}'.")
            prompt_record = db.query(Prompt).filter(Prompt.name == default_prompt_name).first()

        # If still not found (even the default), create it from environment variables
        if not prompt_record:
            logger.info(f"Prompt record not found in DB. Creating '{default_prompt_name}' from environment variables.")
            prompt_record = Prompt(
                name=default_prompt_name,
                is_hum_agent_allow_prompt=os.getenv("is_hum_agent_allow_prompt"),
                no_hum_agent_allow_prompt=os.getenv("no_hum_agent_allow_prompt"),
                summary_prompt=os.getenv("summary_prompt")
            )
            db.add(prompt_record)
            db.flush()
            logger.info(f"Created new Prompt record with ID: {prompt_record.id}")
        else:
            logger.info(f"Using Prompt record with ID: {prompt_record.id}")

        new_tenant = Tenant(
            tenant_id=request.tenant_id,
            tenant_name=request.tenant_name,
            prompt_template_id=prompt_record.id,
            prompt_type=requested_prompt_type, # Store the intended type
            tenant_website=request.tenant_website,
            tenant_knowledge_base=request.tenant_knowledge_base,
            tenant_text=request.tenant_text,
            tenant_document=request.tenant_document,
            is_hum_agent_allow=request.is_hum_agent_allow,
            conf_level=request.conf_level,
            sentiment_threshold=request.sentiment_threshold,
            message_tone=request.message_tone,
            ticket_type=request.ticket_type,
            chatbot_greeting=request.chatbot_greeting,
            # db_uri=request.db_uri
        )
        db.add(new_tenant)
        db.commit()
        
        # Trigger AI Indexing (similar to initialize_vector_store)
        logger.info(f"Tenant {request.tenant_id} committed. Triggering vector store initialization.")
        initialize_vector_store(request.tenant_id)
        
        return {"status": "success", "message": "Tenant onboarded successfully"}
        # return {"status": "success", "message": "Tenant onboarded successfully", "prompt_id": prompt_record.id}

    except Exception as e:
        db.rollback()
        logger.error(f"Onboarding error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.post("/update/", 
          summary="Update Tenant Configuration", 
          description="Updates an existing tenant's profile fields and triggers knowledge base re-indexing.")
async def update_endpoint(request: UpdateRequest):
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.tenant_id == request.tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        
        update_data = request.dict(exclude_unset=True)
        logger.info(f"Raw data: {update_data}")
        for key, value in update_data.items():
            if key != "tenant_id" and hasattr(tenant, key):
                setattr(tenant, key, value)
        
        db.commit()
        # Re-initialize vector store if content changed (optional check)
        initialize_vector_store(request.tenant_id)
        return {"status": "success", "message": "Tenant updated."}
    except Exception as e:
        db.rollback()
        logger.error(f"Update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/fetch/", 
         summary="Detailed Tenant Fetch", 
         description="Retrieves specific tenant data including greeting and raw knowledge text.")
async def fetch_endpoint(tenant_id: str):
    db = SessionLocal()
    logger.info(f"Fetch endpoint called for tenant {tenant_id}")
    try:
        tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant_id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        return {
            "tenant_id": tenant.tenant_id,
            "tenant_name": tenant.tenant_name,
            "chatbot_greeting": tenant.chatbot_greeting,
            "tenant_text": tenant.tenant_text,
            "tenant_document": tenant.tenant_document,
            "tenant_website": tenant.tenant_website,
            "tenant_knowledge_base": tenant.tenant_knowledge_base,
            "is_hum_agent_allow": tenant.is_hum_agent_allow,
            "conf_level": tenant.conf_level,
            "sentiment_threshold": tenant.sentiment_threshold,
            "message_tone": tenant.message_tone,
            "ticket_type": tenant.ticket_type,
        }
    finally:
        db.close()



  
@app.post("/chat/", 
          summary="Chat with AI Agent", 
          description="Sends a message to the AI agent for a specific tenant and conversation. Supports file attachments.")
async def chat_endpoint_robust(
    message_content: str = Form(..., description="The user's text message"),
    conversation_id: str = Form(..., description="Unique ID for the chat session"),
    tenant_id: str = Form(..., description="Unique ID for the tenant"),
    summarization_request: bool = Form(False, description="Whether to request a summary of the conversation"),
    user_msg_attach: Optional[UploadFile] = File(None, description="Optional file attachment for the message")
):
    try:
        logger.info(f"Chat View Called (Global LLM)")
        # --- Trigger Global LLM Check/Creation with resilience ---
        try:
            get_or_create_global_llm()
        except Exception as llm_err:
            logger.warning(f"⚠️ LLM config fetch failed (will use fallback): {str(llm_err)[:150]}")
            # Continue anyway — get_or_create_global_llm has built-in fallback
        
        file_path = None
        if user_msg_attach:
            # Save file locally
            file_path = f"chat_attachments/{user_msg_attach.filename}"
            os.makedirs("chat_attachments", exist_ok=True)
            with open(file_path, "wb") as buffer:
                buffer.write(await user_msg_attach.read())

        response = await process_message(
            message_content=message_content,
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            file_path=file_path,
            summarization_request=summarization_request
        )
        return response
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Chat error: {error_msg[:300]}")
        
        # Distinguish between connection errors and other errors
        if "gone away" in error_msg or "connection" in error_msg.lower():
            status_code = 503  # Service Unavailable
            detail = "Database temporarily unavailable. Please retry in a moment."
        else:
            status_code = 500
            detail = str(e)
        
        raise HTTPException(status_code=status_code, detail=detail)
  


@app.on_event("startup")
def startup_event():
    init_db()

# --- Helper Functions ---

def extract_llm_text(response: Any, log: logging.Logger) -> str:
    """
    Safely extract text from an LLM response object.
    Handles None, unexpected structures, and multiple formats.
    """
    # 1. Null response check
    if response is None:
        log.error("llm_client.invoke() returned None. Check LLM configuration and network.")
        return "LLM_ERROR: No response received."

    # 2. Expected attribute check
    if not hasattr(response, "content"):
        log.error(f"Response object lacks 'content' attribute. Type: {type(response)}")
        log.debug(f"Full Response Object: {response}")
        # Fallback for string response
        if isinstance(response, str):
             return response
        return "LLM_ERROR: Invalid response structure."

    raw_text = None

    # 3. Case: content is a list of dicts
    if isinstance(response.content, list):
        for item in response.content:
            if isinstance(item, dict) and "text" in item:
                raw_text = item["text"]
                break  # stop at first valid text block

    # 4. Case: content is a plain string
    elif isinstance(response.content, str):
        raw_text = response.content

    # 5. Fallback if nothing extracted
    if not raw_text:
        log.error(f"Could not extract raw text from LLM response content of type: {type(response.content)}")
        return "LLM_ERROR: Could not parse LLM response text."

    return raw_text


#Utility Endpoints   



@app.post("/utility/llm_speed/", summary="Hello AI Endpoint", description="Simple endpoint to test AI responses without tool calls.")
async def say_hello_ai(request: HelloAIRequest):
    """Simple AI chat endpoint for quick verification (no tool calls)."""
    try:
        logger.info(f"Hello AI Endpoint called with message: {request.user_message}")
        
        # --- Get Global LLM Config ---
        db = SessionLocal()
        try:
            llm_config = db.query(LLM).first()
            if not llm_config:
                # Auto-create default Gemini
                llm_config = LLM(
                    name="gemini",
                    model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
                    key=os.getenv("GEMINI_API_KEY", "")
                )
                db.add(llm_config)
                db.commit()
                db.refresh(llm_config)
        finally:
            db.close()
        
        # --- Instantiate LLM WITHOUT tools ---
        from langchain_google_genai import ChatGoogleGenerativeAI
        from .ollama_service import OllamaService
        
        if llm_config.name.lower() == "gemini":
            simple_llm = ChatGoogleGenerativeAI(
                model=llm_config.model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
                google_api_key=os.getenv("GEMINI_API_KEY"),  # Always from env
                temperature=0
            )
        elif llm_config.name.lower() == "ollama_cloud":
            # Use ollama_cloud as the model name to trigger cloud API
            simple_llm = OllamaService(
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),  # Not used for cloud
                username=os.getenv("OLLAMA_USERNAME", ""),  # Not used for cloud
                password=os.getenv("OLLAMA_PASSWORD", ""),  # Not used for cloud
                model="ollama_cloud"  # Special sentinel value
            )
        else:  # ollama (local)
            simple_llm = OllamaService(
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                username=os.getenv("OLLAMA_USERNAME", ""),
                password=os.getenv("OLLAMA_PASSWORD", ""),
                model=llm_config.model or os.getenv("OLLAMA_MODEL", "gpt-oss-safeguard:20b")
            )
        
        start_time = time.time()
        response = await simple_llm.ainvoke(request.user_message)
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        # Extract content from AIMessage
        ai_text = response.content if hasattr(response, 'content') else str(response)
        
        logger.info(f"✅ Hello AI Response ({llm_config.name}): {ai_text[:100]}... | Duration: {duration}s")
        
        return {
            "response": ai_text,
            "duration_seconds": duration,
            "llm_used": llm_config.name,
            "model": llm_config.model
        }
    except Exception as e:
        logger.error(f"Hello AI error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/utility/updateLLM/", summary="Update Global LLM Configuration", description="Updates the single global LLM configuration.")
async def update_llm_endpoint(request: LLMUpdate):
    db = SessionLocal()
    try:
        # Singleton: Always get or create the single LLM record
        llm_config = db.query(LLM).first()
        if not llm_config:
            # Auto-create single Gemini record if missing
            llm_config = LLM(
                name="gemini",
                model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
            )
            db.add(llm_config)
            db.commit()
            db.refresh(llm_config)
        
        # Update the singleton LLM record
        if request.name:
            llm_config.name = request.name
        if request.model:
            llm_config.model = request.model
            
        db.commit()
        return {"status": "success", "message": "Global LLM configuration updated"}
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating LLM: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.post("/utility/prompt/", 
          summary="Manage System Prompts", 
          description="Creates or updates a reusable system prompt set for agent behaviors.")
async def prompt_endpoint(request: PromptRequest):
    db = SessionLocal()
    try:
        # Check if prompt with this name already exists
        prompt = db.query(Prompt).filter(Prompt.name == request.name).first()
        if prompt:
            prompt.is_hum_agent_allow_prompt = request.is_hum_agent_allow_prompt
            prompt.no_hum_agent_allow_prompt = request.no_hum_agent_allow_prompt
            prompt.summary_prompt = request.summary_prompt
            msg = "Prompt updated successfully"
        else:
            new_prompt = Prompt(
                name=request.name,
                is_hum_agent_allow_prompt=request.is_hum_agent_allow_prompt,
                no_hum_agent_allow_prompt=request.no_hum_agent_allow_prompt,
                summary_prompt=request.summary_prompt
            )
            db.add(new_prompt)
            msg = "Prompt created successfully"
        
        db.commit()
        return {"status": "success", "message": msg}
    except Exception as e:
        db.rollback()
        logger.error(f"Prompt error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/utility/fetch_prompt/", 
          summary="Fetch  System Prompts", 
          description="Fetches a reusable system prompt set for agent behaviors.")
async def fetch_prompt_endpoint(request: PromptRequest):
    db = SessionLocal()
    try:
        # Check if prompt with this name already exists
        prompt = db.query(Prompt).filter(Prompt.name == request.name).first()
        if prompt:
            return {"status": "success", "message": "Prompt fetched successfully", "prompt": prompt}
        else:
            return {"status": "error", "message": "Prompt not found"}
    except Exception as e:
        db.rollback()
        logger.error(f"Prompt error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


def get_or_create_global_llm() -> LLM:
    """Helper to fetch singleton LLM or create default Gemini record.
    
    Supported LLM names:
    - 'gemini': Google Gemini API
    - 'ollama': Local Ollama instance
    - 'ollama_cloud': Ollama Cloud API (requires OLLAMA_API_KEY)
    """
    # Retry logic for resilience against transient DB connection issues
    max_retries = 3
    retry_delay = 0.5  # seconds
    
    for attempt in range(max_retries):
        db = SessionLocal()
        try:
            logger.info(f"🔍 Fetching or creating global LLM configuration (attempt {attempt + 1}/{max_retries})...")
            llm_config = db.query(LLM).first()
            
            if not llm_config:
                logger.info("No LLM record found. Creating default Gemini configuration.")
                
                # Create single Gemini record
                llm_config = LLM(
                    name="gemini",
                    model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
                )
                db.add(llm_config)
                db.commit()
                db.refresh(llm_config)
                
                logger.info(f"✅ Created Gemini LLM (ID: {llm_config.id}, Model: {llm_config.model})")
            else:
                logger.info(f"✅ Retrieved LLM config: {llm_config.name} - {llm_config.model}")
                
                # Validate ollama_cloud configuration
                if llm_config.name.lower() == "ollama_cloud":
                    api_key = os.getenv("OLLAMA_API_KEY")
                    if not api_key:
                        logger.warning("⚠️ ollama_cloud selected but OLLAMA_API_KEY not set in environment")
                    else:
                        logger.info(f"🔑 Ollama Cloud API key configured")
                
            return llm_config
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Error fetching/creating LLM (attempt {attempt + 1}): {error_msg[:200]}")
            
            # If this is a connection error and we have retries left, wait and retry
            if attempt < max_retries - 1 and ("gone away" in error_msg or "connection" in error_msg.lower()):
                import time
                wait_time = retry_delay * (2 ** attempt)  # exponential backoff
                logger.warning(f"⏳ Retrying in {wait_time:.1f}s due to connection issue...")
                time.sleep(wait_time)
                continue
            
            # All retries exhausted or non-recoverable error
            logger.warning(f"⚠️ Could not connect to database after {max_retries} attempts. Using fallback LLM config.")
            fallback_llm = LLM(
                name=os.getenv("FALLBACK_LLM_NAME", "ollama_cloud"),
                model=os.getenv("FALLBACK_LLM_MODEL", "gpt-oss:120b")
            )
            logger.info(f"🔄 Fallback LLM: {fallback_llm.name} - {fallback_llm.model}")
            return fallback_llm
            
        finally:
            db.close()




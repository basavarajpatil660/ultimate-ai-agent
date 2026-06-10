import os
import sys
import traceback
from datetime import datetime

from core.memory import load_memory, save_memory, reset_daily_budget, update_budget
from core.router import classify_task, detect_language
from core.formatter import format_output
from core.delivery import send_text, send_image, send_audio, send_alert, send_email

from agents.llm_agent import call_llm
from agents.image_agent import generate_image
from agents.vision_agent import analyze_image
from agents.search_agent import research_and_synthesize
from agents.content_agent import generate_content
from agents.voice_agent import text_to_speech

def main():
    try:
        # Load memory & reset budget if needed
        memory = load_memory()
        memory = reset_daily_budget(memory)
        
        # Get env vars
        prompt = os.environ.get("INPUT_PROMPT", "").strip()
        mode = os.environ.get("INPUT_MODE", "auto")
        
        telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        gmail = os.environ.get("GMAIL_ADDRESS")
        gmail_pw = os.environ.get("GMAIL_APP_PASSWORD")
        
        if not prompt and mode == "auto":
            # Default tasks
            idea_res = call_llm("Generate one unique content idea for NickPlays YouTube channel (gaming/Crew Motorfest). Return only the idea.")
            news_res = call_llm("Generate one short AI news briefing bullet point.")
            
            if idea_res:
                send_text(telegram_token, chat_id, f"🎮 *Content Idea:*\n{idea_res.get('result', '')}\n_Provider: {idea_res.get('provider', '')}_")
            if news_res:
                send_text(telegram_token, chat_id, f"📰 *AI News:*\n{news_res.get('result', '')}\n_Provider: {news_res.get('provider', '')}_")
                
            time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
            send_email(gmail, gmail_pw, gmail, "🤖 Agent needs your input", f"Your AI agent ran at {time_str} but received no prompt. Reply with what you want it to do next time.")
            
            # Update memory
            memory["run_count_today"] += 1
            save_memory(memory)
            sys.exit(0)
            
        if prompt:
            # Process actual prompt
            has_image = False
            task_type = classify_task(prompt, has_image)
            lang = detect_language(prompt)
            
            if lang == "hindi/hinglish":
                prompt += " (Please respond in Hindi/Hinglish)"
                
            provider_used = "unknown"
            result_data = None
            
            if task_type in ["FACTUAL", "CREATIVE", "REASONING", "CODE", "SUMMARIZE", "TRANSLATE"]:
                res = call_llm(prompt)
                if res:
                    result_data = res["result"]
                    provider_used = res["provider"]
                    
            elif task_type in ["REALTIME", "RESEARCH"]:
                res = research_and_synthesize(prompt)
                if res:
                    result_data = res["result"]
                    provider_used = res["provider"]
                    
            elif task_type == "IMAGE_GEN":
                res = generate_image(prompt)
                if res:
                    result_data = res
                    provider_used = res["provider"]
                    
            elif task_type == "IMAGE_READ":
                image_path = "/tmp/input.png" if os.path.exists("/tmp/input.png") else "input.png"
                if os.path.exists(image_path):
                    res = analyze_image(image_path, prompt)
                    if res:
                        result_data = res["result"]
                        provider_used = res["provider"]
                else:
                    result_data = "No image found to analyze."
                    
            elif task_type == "CONTENT":
                res = generate_content(prompt)
                if res:
                    result_data = res["result"]
                    provider_used = res["provider"]
                    
            elif task_type == "VOICE_OUT":
                res_text = call_llm(prompt)
                if res_text:
                    text_str = res_text["result"]
                    audio_res = text_to_speech(text_str)
                    if audio_res:
                        result_data = audio_res
                        provider_used = f"llm:{res_text['provider']}, voice:{audio_res['provider']}"
                    else:
                        result_data = text_str
                        task_type = "text" # Fallback to text
                        provider_used = res_text["provider"]
                        
            if result_data:
                formatted = format_output(result_data, task_type, provider_used)
                if formatted["type"] == "text":
                    send_text(telegram_token, chat_id, formatted["content"])
                elif formatted["type"] == "image":
                    send_image(telegram_token, chat_id, formatted["file_path"], formatted["caption"])
                elif formatted["type"] == "audio":
                    send_audio(telegram_token, chat_id, formatted["file_path"], formatted["caption"])
                
                if provider_used == "mistral":
                    update_budget("mistral", 500)
                elif provider_used == "cerebras":
                    update_budget("cerebras", 500)
                elif provider_used == "groq":
                    update_budget("groq", 1)
            else:
                send_text(telegram_token, chat_id, "Failed to process task across all providers.")
                
            # Update memory
            memory["run_count_today"] += 1
            if "tasks_today" not in memory:
                memory["tasks_today"] = []
            memory["tasks_today"].append({
                "prompt": prompt,
                "type": task_type,
                "provider": provider_used,
                "time": datetime.now().isoformat()
            })
            save_memory(memory)
            
    except Exception as e:
        telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        error_msg = f"Agent Crash:\n{traceback.format_exc()}"
        send_alert(telegram_token, chat_id, error_msg[:4000])
        sys.exit(1)

if __name__ == "__main__":
    main()

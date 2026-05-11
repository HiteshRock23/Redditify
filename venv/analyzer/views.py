import os
import markdown
from openai import OpenAI
from django.shortcuts import render
from django.conf import settings
from django.views.decorators.http import require_http_methods
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# --- IMPORTANT FOR BEGINNERS ---
# Initialize the client using your API key from the .env file
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ.get("NVIDIA_API_KEY")
)


import json
import re

# OLD LOGIC (DEPRECATED - replaced by /full_post_analysis)
# def analyze_post(request):
#     context = {}
#     
#     if request.method == "POST":
#         # 1. Get data from the submitted form
#         title = request.POST.get("title", "").strip()
#         body = request.POST.get("body", "").strip()
#         action = request.POST.get("action", "analyze") # detect which button was clicked
#         
#         # 2. Basic Validation
#         if not title or not body:
#             context["error"] = "Both Title and Body are required."
#             return render(request, "analyzer/index.html", context)
#             
#         context["title"] = title
#         context["body"] = body
#             
#         if action == "analyze":
#             # 3. Define the Prompt for Analysis
#             prompt = f"""Analyze the following Reddit post.
# 
# Title: {title}
# Body: {body}
# 
# Return exactly in this format using Markdown:
# **Score:** [Score 0-100]
# 
# **Issues:**
# * [Issue 1]
# * [Issue 2]
# 
# **Suggestions:**
# * [Suggestion 1]
# * [Suggestion 2]
# 
# **Tone:** [Tone description]
# 
# **Readability:** [Readability description]
# 
# Keep it concise and practical.
# """
#             
#             # 4. Call the AI Model
#             try:
#                 response = client.chat.completions.create(
#                     model="meta/llama-3.1-8b-instruct",
#                     messages=[{"role": "user", "content": prompt}],
#                     temperature=0.2,
#                     max_tokens=1024,
#                 )
#                 # 5. Convert Markdown response to HTML
#                 feedback_html = markdown.markdown(response.choices[0].message.content)
#                 context["feedback"] = feedback_html
#                 
#             except Exception as e:
#                 context["error"] = f"An error occurred while analyzing: {str(e)}"
#                 
#         elif action == "improve":
#             # 3. Use the predefined workflow prompt
#             prompt = f"/rewrite_post\n\nTitle: {title}\nBody: {body}"
#             
#             # 4. Call the AI Model
#             try:
#                 response = client.chat.completions.create(
#                     model="meta/llama-3.1-8b-instruct",
#                     messages=[{"role": "user", "content": prompt}],
#                     temperature=0.2,
#                     max_tokens=1024,
#                 )
#                 # 5. Convert Markdown response to HTML
#                 improved_html = markdown.markdown(response.choices[0].message.content)
#                 context["improved_post"] = improved_html
#                 
#             except Exception as e:
#                 context["error"] = f"An error occurred while improving: {str(e)}"
#                 
#         # 6. Fetch Subreddit Suggestions (Runs for both actions)
#         subreddit_prompt = f"/suggest_subreddits\n\nContent: {title} {body}"
#         try:
#             subreddit_response = client.chat.completions.create(
#                 model="meta/llama-3.1-8b-instruct",
#                 messages=[{"role": "user", "content": subreddit_prompt}],
#                 temperature=0.2,
#                 max_tokens=1024,
#             )
#             context["subreddits"] = markdown.markdown(subreddit_response.choices[0].message.content)
#         except Exception as e:
#             # We append the error so we don't overwrite previous errors
#             existing_error = context.get("error", "")
#             context["error"] = f"{existing_error} | Subreddit error: {str(e)}" if existing_error else f"Subreddit error: {str(e)}"
#             
#     # If GET request or after processing POST, render the template
#     return render(request, "analyzer/index.html", context)


def analyze_post(request):
    """
    Unified workflow to fetch analysis, rewrite, and subreddit suggestions in a single call.
    Data is parsed as JSON to easily populate the structured frontend template.
    """
    context = {}
    
    if request.method == "POST":
        # 1. Get data from the submitted form
        title = request.POST.get("title", "").strip()
        body = request.POST.get("body", "").strip()
        
        # 2. Basic Validation
        if not title or not body:
            context["error"] = "Both Title and Body are required."
            return render(request, "analyzer/index.html", context)
            
        context["title"] = title
        context["body"] = body
            
        # 3. Read the prompt from the workflow file
        workflow_path = settings.BASE_DIR / ".agents" / "workflows" / "full_post_analysis.md"
        try:
            with open(workflow_path, "r", encoding="utf-8") as f:
                workflow_content = f.read()
            # Replace placeholders with actual user input
            prompt = workflow_content.replace("{{title}}", title).replace("{{body}}", body)
            prompt += "\n\nCRITICAL INSTRUCTION: Return ONLY a valid JSON object strictly following the structure above. Do not include markdown blocks like ```json or any conversational text before or after the JSON. You MUST properly escape any double quotes or newlines within string values."
        except FileNotFoundError:
            context["error"] = "Workflow configuration file missing."
            return render(request, "analyzer/index.html", context)
        
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                # 4. Call the AI Model
                response = client.chat.completions.create(
                    model="meta/llama-3.1-8b-instruct",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=2048,
                )
                
                # Extract only the JSON object, ignoring any conversational text or markdown formatting
                response_content = response.choices[0].message.content.strip()
                start_idx = response_content.find('{')
                end_idx = response_content.rfind('}')
                
                if start_idx != -1 and end_idx != -1 and end_idx >= start_idx:
                    response_content = response_content[start_idx:end_idx+1]
                
                # Simple LLM JSON Hallucination Repairs
                # 1. Fix common extra closing bracket typo
                response_content = re.sub(r'\}\s*\},', '},', response_content)
                # 2. Fix trailing commas
                response_content = re.sub(r',\s*([\]}])', r'\1', response_content)
                
                # 5. Parse JSON and validate (allow unescaped newlines with strict=False)
                data = json.loads(response_content, strict=False)
                
                analysis = data.get("analysis", {})
                rewrite = data.get("rewrite", {})
                subreddits = data.get("subreddits", [])
                
                # Output Quality Enforcement
                is_valid = True
                
                # Check rewrite
                if not rewrite.get("title") or not rewrite.get("body") or len(rewrite.get("body", "")) < 10:
                    is_valid = False
                    
                # Check subreddits (at least 5)
                if not isinstance(subreddits, list) or len(subreddits) < 5:
                    is_valid = False
                    
                # Check issues and suggestions
                if not analysis.get("issues") or not analysis.get("suggestions"):
                    is_valid = False
                    
                if is_valid:
                    # If valid, populate context and break out of retry loop
                    context["analysis"] = analysis
                    context["rewrite"] = rewrite
                    context["subreddits"] = subreddits
                    break
                else:
                    if attempt == max_retries:
                        context["error"] = "Couldn’t generate strong output, please try again."
            except json.JSONDecodeError as jde:
                if attempt == max_retries:
                    context["error"] = "We couldn't process the AI's response correctly. Please try again."
                    # Log the failed content for debugging
                    try:
                        with open("failed_json_log.txt", "w", encoding="utf-8") as logf:
                            logf.write(f"JSONDecodeError: {str(jde)}\n\n")
                            logf.write("=== FAILED CONTENT ===\n")
                            logf.write(response_content)
                    except Exception:
                        pass
            except Exception as e:
                if attempt == max_retries:
                    # Masking actual exception for user-friendly error
                    context["error"] = "Something went wrong. Please try again."
            
    # If GET request or after processing POST, render the template
    return render(request, "analyzer/index.html", context)

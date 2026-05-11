import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ.get("NVIDIA_API_KEY")
)

with open('venv/.agents/workflows/full_post_analysis.md', 'r', encoding='utf-8') as f:
    workflow_content = f.read()

prompt = workflow_content.replace('{{title}}', 'My "Test" Title').replace('{{body}}', 'This is a test post body with "quotes" and \n newlines to see what happens.')
prompt += "\n\nCRITICAL INSTRUCTION: Return ONLY a valid JSON object strictly following the structure above. Do not include markdown blocks like ```json or any conversational text before or after the JSON."

for i in range(10):
    print(f"--- ATTEMPT {i+1} ---")
    response = client.chat.completions.create(
        model="meta/llama-3.1-8b-instruct",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=2048
    )

    raw_content = response.choices[0].message.content
    response_content = raw_content.strip()
    start_idx = response_content.find('{')
    end_idx = response_content.rfind('}')

    if start_idx != -1 and end_idx != -1 and end_idx >= start_idx:
        response_content = response_content[start_idx:end_idx+1]

    try:
        data = json.loads(response_content, strict=False)
        print("Success.")
    except json.JSONDecodeError as e:
        print("\n=== JSON DECODE ERROR ===")
        print(e)
        print("\n=== FAILED CONTENT ===")
        print(response_content)
        break

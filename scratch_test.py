import json

s = """{
    "body": "Hello
World"
}"""

try:
    data = json.loads(s, strict=False)
    print("Success:", data)
except Exception as e:
    print("Error:", e)

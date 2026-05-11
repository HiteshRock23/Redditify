---
description: analyze_post
---

Analyze the following Reddit post.

Input:
Title: {{title}}
Body: {{body}}

Return output in JSON format:

{
"score": number (0-100),
"issues": ["list of key problems"],
"suggestions": ["specific improvements"],
"tone": "casual/formal/spammy",
"readability": "easy/medium/hard"
}

Guidelines:

* Be strict but fair in scoring
* Focus on clarity, engagement, and authenticity
* Avoid generic advice

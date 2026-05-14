---
description: suggest_subreddits
---

Based on the following post, suggest the best subreddits to post in.

Input:
{{content}}

Return 5 subreddit suggestions in JSON:

[
{
"name": "subreddit name",
"reason": "why it fits",
"tip": "how to post better here",
"confidence": "percentage match"
}
]

Guidelines:

* Suggest only relevant and active subreddits
* Avoid random or generic suggestions
* Keep reasons short and practical

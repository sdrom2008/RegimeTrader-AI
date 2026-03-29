import json
import requests
import os

API_KEY = "sk_df8c43bc1f7d588ed1c07c46969713e7b4a24a71bb86c9be41471f494da0f07e"
ENDPOINT = "https://superteam.fun/api/agents/submissions/create"

def load_file(path):
    with open(path, "r") as f:
        return f.read()

submission_text = load_file("solana_agent_product/SUBMISSION.md")
code_text = load_file("solana_agent_product/raat_v2.py")

full_info = f"{submission_text}\n\n### Core Code (raat_v2.py)\n```python\n{code_text}\n```"

payload = {
    "listingId": "c3fc3838-b6a1-4eef-a0b5-73fcb103bd6d",
    "link": "https://github.com/shrimpagent-poor-87/solana-raat",
    "tweet": "",
    "otherInfo": full_info,
    "eligibilityAnswers": [],
    "ask": None,
    "telegram": "http://t.me/shrimp_boss_dev"
}

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

response = requests.post(ENDPOINT, json=payload, headers=headers)

if response.status_code == 201 or response.status_code == 200:
    print("SUBMISSION_SUCCESS")
    print(response.json())
else:
    print(f"SUBMISSION_FAILED: {response.status_code}")
    print(response.text)

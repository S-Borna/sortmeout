#!/usr/bin/env python3
"""Test which Claude models are available for your API key."""
import os
import sys

# Ladda API-nyckel
env_file = os.path.expanduser("~/.config/sortmeout/.env")
api_key = None
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            if line.startswith("ANTHROPIC_API_KEY="):
                api_key = line.split("=", 1)[1].strip()

if not api_key:
    print("Ingen API-nyckel hittades")
    sys.exit(1)

print(f"API-nyckel: {api_key[:20]}...{api_key[-10:]}")

import anthropic
client = anthropic.Anthropic(api_key=api_key)

# Testa olika modeller
models = [
    "claude-3-haiku-20240307",
    "claude-3-5-haiku-20241022",
    "claude-3-sonnet-20240229", 
    "claude-3-5-sonnet-20241022",
    "claude-3-opus-20240229",
]

print("\n=== Testar modeller ===")
for model in models:
    try:
        response = client.messages.create(
            model=model,
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}]
        )
        print(f"✅ {model} - FUNGERAR")
    except anthropic.NotFoundError as e:
        print(f"❌ {model} - EJ TILLGÄNGLIG")
    except anthropic.PermissionDeniedError as e:
        print(f"🚫 {model} - INGEN BEHÖRIGHET")
    except anthropic.RateLimitError as e:
        print(f"⏳ {model} - RATE LIMITED (men finns)")
    except Exception as e:
        print(f"❓ {model} - FEL: {type(e).__name__}")

print("\n=== Möjliga orsaker till begränsningar ===")
print("1. Gratis trial-konto - har ofta bara tillgång till Haiku")
print("2. Workspaces - API-nycklar kan ha olika behörigheter")
print("3. Betalplan - vissa modeller kräver högre tier")
print("4. Region - vissa modeller kan vara regionsbegränsade")
print("\nKolla på https://console.anthropic.com för att se ditt konto.")

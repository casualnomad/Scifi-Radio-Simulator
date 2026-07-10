# config.py
#LOCAL_LLAMA_SERVER_URL = "http://localhost:8080/chat/completions"

STORY_MODEL = "bartowski/Llama-3.2-3B-Instruct-uncensored-GGUF:F16"
STORY_TEMPERATURE = 0.9
STORY_MAX_TOKENS = 2500

TRANSMISSION_MODEL = "MaziyarPanahi/Mistral-7B-Instruct-v0.3-GGUF:Q4_K_M"
TRANSMISSION_TEMPERATURE = 1.5
TRANSMISSION_MAX_TOKENS = 500

WORLD_STATE_PATH = "WorldState/worldstate.json"
TICK_UPDATE_INTERVAL = 6

API_STORY_MODEL = "claude-haiku-4-5-20251001"
API_TRANSMISSION_MODEL = "claude-haiku-4-5-20251001"
# config.py
#LOCAL_LLAMA_SERVER_URL = "http://localhost:8080/chat/completions"
LLAMA_SERVER_URL = "http://192.168.4.77:8080/v1/chat/completions"

STORY_MODEL = "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF:Q6_K"
STORY_TEMPERATURE = 0.9
STORY_MAX_TOKENS = 2500

TRANSMISSION_MODEL = "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF:Q6_K"
TRANSMISSION_TEMPERATURE = 0.9
TRANSMISSION_MAX_TOKENS = 500

WORLD_STATE_PATH = "WorldState/worldstate.json"
TICK_UPDATE_INTERVAL = 7

API_STORY_MODEL = "claude-haiku-4-5-20251001"
API_TRANSMISSION_MODEL = "claude-haiku-4-5-20251001"
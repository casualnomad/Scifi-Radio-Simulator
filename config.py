# config.py
LOCAL_LLAMA_SERVER_URL = "http://localhost:8080/v1/chat/completions"
LLAMA_SERVER_URL = "http://192.168.7.114:8080/v1/chat/completions"




STORY_MODEL = "gemma-4-e4b-it:Q8_0"
STORY_TEMPERATURE = 0.9
STORY_MAX_TOKENS = 2500

TRANSMISSION_MODEL = "prism-ml/Bonsai-8B-gguf:Q1_0"
TRANSMISSION_TEMPERATURE = 0.9
TRANSMISSION_MAX_TOKENS = 500

WORLD_STATE_PATH = "WorldState/worldstate.json"
TICK_UPDATE_INTERVAL = 5
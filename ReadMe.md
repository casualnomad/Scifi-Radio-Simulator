# Scifi Radio Simulator

This project simulates a dynamic space radio communication network and world state evolution using Large Language Models (LLMs). It models an ongoing narrative where multiple starships communicate via radio chatter, and the overall universe state advances over time.

## 🚀 Features

*   **Dynamic World State Management:** Maintains a persistent `worldstate.json` file tracking all aspects of the simulated universe.
*   **Radio Chatter Simulation:** Generates realistic, constrained communications between ships using an LLM API call (`generate_radio_chatter`).
*   **World Evolution Engine:** Periodically advances the simulation state (e.g., every 10 ticks) by calling a second LLM endpoint to update ship statuses, active events, and the overall story arc (`generate_world_state`).
*   **Text-to-Speech (TTS):** Converts generated radio chatter text into audible sound files for immersive playback.
*   **Modular Architecture:** Separates concerns into distinct modules: `LLM/` (for prompt management), `TTS/` (for audio handling), and `WorldState/` (for state persistence).

## ⚙️ Project Structure Overview

```
Scifi-Radio-Simulator/
├── config.py          # Global configuration variables (API URLs, model names, etc.)
├── main.py            # Main execution loop: Initializes the simulation and runs the chat/world update cycle.
├── LLM/               # Handles system prompts and communication logic for LLMs.
│   └── systemprompts.py
├── TTS/               # Modules for Text-to-Speech generation and audio playback.
│   ├── backgroundsfx.py
│   ├── texttospeech.py
│   └── voicemodulation.py
├── WorldState/        # Manages the persistent state of the simulation.
│   ├── worldstate.json # The current saved state of the universe.
│   ├── worldstate.py   # Core logic for loading, saving, and updating the world state.
│   └── shipgen.py      # Logic for generating new ships when old ones depart/are destroyed.
├── SFX/               # Sound effect assets (e.g., Background.wav).
└── snapshots/         # Directory containing historical world state snapshots.
```

## 🛠️ Setup and Installation

### Prerequisites

*   Python 3.8+
*   `requests` library for API calls.
*   `pydub` and `pygame` for audio handling.
*   A running LLM server accessible at the configured URL (default: `http://localhost:8080/v1/chat/completions`).

### Installation Steps

1.  **Install Python Dependencies:**
    ```bash
    pip install requests pydub pygame
    ```

2.  **Configure API Endpoint:**
    Ensure your LLM server is running and update `config.py` with the correct `LLAMA_SERVER_URL`.

3.  **Run the Simulator:**
    Execute the main script to start the simulation loop:
    ```bash
    python main.py
    ```

## 💡 Usage Notes

*   **Simulation Flow:** The `main()` function runs an infinite loop, periodically calling `generate_radio_chatter()` for communication and `generate_world_state()` to advance the narrative time.
*   **State Persistence:** All world changes are saved to `WorldState/worldstate.json`. Snapshots are also taken in the `snapshots/` directory.
*   **LLM Prompts:** The system prompts are carefully crafted in `LLM/systemprompts.py` to enforce strict output formats, ensuring reliable parsing of LLM responses.

## 🐛 Known Issues / To-Do

*   [ ] Implement robust error handling for TTS generation failures.
*   [ ] Add logging functionality for tracking simulation ticks and major events.
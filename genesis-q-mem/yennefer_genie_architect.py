import os
import time
import random
import logging
import google.generativeai as genai

# Get absolute paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(REPO_ROOT, "yennefer-observatory/src/components/mutations")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "GenieMutation.jsx")

# Add script dir to path for imports if needed, though python does it automatically
import sys
if SCRIPT_DIR not in sys.path:
    sys.path.append(SCRIPT_DIR)

from swarm_config import SWARM_CONFIG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("GenieArchitect")

GENERATION_INTERVAL = 300  # 5 minutes

def get_api_key():
    """Get API key from environment variable"""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("GOOGLE_API_KEY environment variable not set")
        return None
    return api_key

def setup_genai():
    """Configure Google Generative AI"""
    api_key = get_api_key()
    if not api_key:
        return None

    genai.configure(api_key=api_key)
    model_name = SWARM_CONFIG.get("supervisor_model", "gemini-2.0-flash-exp")
    return genai.GenerativeModel(model_name)

def generate_mutation(model):
    """Generate a React Three Fiber component"""
    themes = [
        "Cyberpunk Neon City", "Floating Crystal Islands", "Quantum Fractal Landscape",
        "Void Geometry", "Bioluminescent Forest", "Abstract Data Flow",
        "Retro Grid Horizon", "Celestial Mechanics", "Hyper-Structure",
        "Liquid Metal Ocean", "Glitch Dimension", "Minimalist Zen Garden"
    ]
    theme = random.choice(themes)
    logger.info(f"Generating mutation with theme: {theme}")

    # Note: Double braces {{ }} are used to escape { } in the f-string for JS code
    prompt = f"""
    You are Project Genie, an advanced AI architect.
    Create a React Three Fiber (R3F) component that renders a unique, procedural 3D world or object based on the theme: "{theme}".

    Requirements:
    1. The code MUST be valid JSX.
    2. It MUST export a default function component named `GenieMutation`.
    3. It MUST accept `props`: {{ coherence, balance }}.
       - Use `coherence` (0-100) to control stability, noise, or structure.
       - Use `balance` (float) to control scale, intensity, or count.
    4. Use `useFrame` from `@react-three/fiber` for animation.
    5. Use `useRef` from `react` for references.
    6. Use standard geometries (Box, Sphere, Torus, etc.) or `@react-three/drei` components if appropriate (e.g., `Stars`, `Float`).
    7. Do NOT import `Canvas`. The component will be rendered inside an existing Canvas.
    8. Do NOT use external assets (textures/models) unless generated procedurally or using standard materials.
    9. Keep the code self-contained.
    10. Return ONLY the code, no markdown formatting (or wrap in ```jsx blocks which I will strip).

    Example Structure:
    ```jsx
    import React, {{ useRef }} from 'react';
    import {{ useFrame }} from '@react-three/fiber';
    import {{ Float }} from '@react-three/drei';

    export default function GenieMutation({{ coherence, balance }}) {{
      const ref = useRef();
      useFrame((state) => {{
        // Animation logic using coherence
        ref.current.rotation.x += 0.01 * (coherence / 100);
      }});

      return (
        <group ref={{ref}}>
          <mesh>
            <boxGeometry />
            <meshStandardMaterial color="hotpink" />
          </mesh>
        </group>
      );
    }}
    ```
    """

    try:
        response = model.generate_content(prompt)
        code = response.text

        # Clean up markdown code blocks if present
        if "```jsx" in code:
            code = code.split("```jsx")[1].split("```")[0].strip()
        elif "```javascript" in code:
            code = code.split("```javascript")[1].split("```")[0].strip()
        elif "```" in code:
            code = code.split("```")[1].split("```")[0].strip()

        return code
    except Exception as e:
        logger.error(f"Error generating mutation: {e}")
        return None

def save_mutation(code):
    """Save the generated code to file"""
    if not code:
        return False

    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(OUTPUT_FILE, "w") as f:
            f.write(code)
        logger.info(f"Mutation saved to {OUTPUT_FILE}")
        return True
    except Exception as e:
        logger.error(f"Error saving mutation: {e}")
        return False

def main():
    logger.info("Starting Yennefer Genie Architect...")
    model = setup_genai()
    if not model:
        logger.error("Failed to initialize GenAI. Exiting.")
        return

    while True:
        logger.info("Dreaming up a new world...")
        code = generate_mutation(model)
        if code:
            save_mutation(code)

        logger.info(f"Sleeping for {GENERATION_INTERVAL} seconds...")
        time.sleep(GENERATION_INTERVAL)

if __name__ == "__main__":
    main()

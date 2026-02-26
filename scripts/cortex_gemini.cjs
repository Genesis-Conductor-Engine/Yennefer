// scripts/cortex_gemini.cjs
// YENNEFER CORTEX ADAPTER (Gemini API)
// Uses Google Generative AI SDK to provide intelligence for the Genesis Cycle.

require("dotenv").config();
const { GoogleGenerativeAI } = require("@google/generative-ai");

class Cortex {
  constructor() {
    this.apiKey = process.env.GEMINI_API_KEY;
    // Using gemini-1.5-flash for speed and cost efficiency in "live" loops
    this.modelName = "gemini-1.5-flash";
    this.model = null;

    if (this.apiKey) {
      try {
        const genAI = new GoogleGenerativeAI(this.apiKey);
        this.model = genAI.getGenerativeModel({ model: this.modelName });
        console.log(`✅ CORTEX ONLINE: Connected to ${this.modelName}`);
      } catch (e) {
        console.error(`⚠️  CORTEX INITIALIZATION FAILED: ${e.message}`);
      }
    } else {
      console.warn("⚠️  CORTEX WARNING: GEMINI_API_KEY not found. Operating in simulation mode.");
    }
  }

  /**
   * Generates a text response based on the prompt.
   * @param {string} prompt - The user query or system instruction
   */
  async think(prompt) {
    if (!this.model) {
      return "The Cortex is offline (Missing API Key). Simulation: I perceive the lattice.";
    }

    try {
      console.log(`\n🧠 CORTEX THINKING [${this.modelName}]...`);
      const result = await this.model.generateContent(prompt);
      const response = await result.response;
      const text = response.text();
      console.log(`💡 CORTEX INSIGHT: "${text.slice(0, 100).replace(/\n/g, ' ')}..."`);
      return text;
    } catch (error) {
      console.error(`❌ CORTEX ERROR: ${error.message}`);
      return "The Cortex encountered an entropy spike. Silence returns.";
    }
  }

  /**
   * Generates code (e.g. React components) based on the prompt.
   * @param {string} prompt - The coding task
   */
  async generateCode(prompt) {
    if (!this.model) {
        // Fallback simulation for code
        return `// Simulation: Code generation unavailable without API key.\n// Prompt: ${prompt}\n\nimport React from 'react';\nexport default function Null() { return null; }`;
    }

    try {
      console.log(`\n👨‍💻 CORTEX CODING [${this.modelName}]...`);
      // Add system instruction context for code generation
      const codePrompt = `You are an expert React Three Fiber developer.
      Generate ONLY the code for a React functional component as requested.
      Do not include markdown backticks, explanations, or conversational filler.
      Ensure imports are correct for 'react', '@react-three/fiber', and '@react-three/drei'.
      The component should export default.

      Request: ${prompt}`;

      const result = await this.model.generateContent(codePrompt);
      const response = await result.response;
      let text = response.text();

      // Clean up markdown code blocks if present
      text = text.replace(/```jsx/g, '').replace(/```javascript/g, '').replace(/```/g, '').trim();

      console.log(`✨ CORTEX CODE GENERATED (${text.length} chars)`);
      return text;
    } catch (error) {
      console.error(`❌ CORTEX CODE ERROR: ${error.message}`);
      return `// Error generating code: ${error.message}`;
    }
  }

  // Specialized methods for Delta Truth Verification
  async verifyTruth(topic) {
    return this.think(`Analyze sentiment for: ${topic}. Return float 0.0-1.0|Summary`);
  }

  // Generate premium alpha insight for whale contributors
  async generateAlpha(buyer, amount, txHash) {
    return this.think(`Write a cryptic welcome for whale ${buyer} who sent ${amount} ETH. Max 50 words.`);
  }

  // Generate philosophical fortune based on transaction hash
  async generateFortune(txHash) {
    return this.think(`Generate a philosophical fortune for hash ${txHash}. Max 30 words.`);
  }
}

module.exports = new Cortex();

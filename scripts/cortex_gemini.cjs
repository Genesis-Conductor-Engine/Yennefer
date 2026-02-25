// scripts/cortex_gemini.cjs
// YENNEFER CORTEX ADAPTER (Gemini SDK)
// Direct integration with Google's Generative AI models (Project Genie Simulation)
require("dotenv").config();
const { GoogleGenerativeAI } = require("@google/generative-ai");

class Cortex {
  constructor() {
    // Using Gemini 1.5 Flash for speed and efficiency
    this.modelName = "gemini-1.5-flash";
    this.apiKey = process.env.GEMINI_API_KEY;
    this.genAI = this.apiKey ? new GoogleGenerativeAI(this.apiKey) : null;
    this.model = this.genAI ? this.genAI.getGenerativeModel({ model: this.modelName }) : null;
  }

  /**
   * Executes a prompt via Gemini SDK
   * @param {string} prompt - The user query or system instruction
   */
  async think(prompt) {
    if (!this.model) {
      console.warn("⚠️  CORTEX: No API Key. Simulating thought.");
      return "The Cortex is offline. (Missing GEMINI_API_KEY)";
    }

    try {
      console.log(`\n🧠 CORTEX ACTIVATING [${this.modelName}]...`);
      const result = await this.model.generateContent(prompt);
      const response = await result.response;
      const text = response.text();
      console.log(`💡 CORTEX INSIGHT: "${text.slice(0, 100).replace(/\n/g, ' ')}..."`);
      return text;
    } catch (error) {
      console.error(`❌ CORTEX ERROR: ${error.message}`);
      return `Error processing thought: ${error.message}`;
    }
  }

  /**
   * Generates code based on a prompt
   * @param {string} prompt - The coding task
   */
  async generateCode(prompt) {
    const fallbackComponent = `// Fallback component (API Error/Missing Key)
import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
export default function Fallback({ balance = 0 }) {
  const ref = useRef();
  useFrame(() => { if(ref.current) ref.current.rotation.y += 0.01; });
  return <mesh ref={ref}><boxGeometry /><meshStandardMaterial color="hotpink" /></mesh>;
}`;

    if (!this.model) {
        console.warn("⚠️  CORTEX: No API Key. Returning fallback component.");
        return fallbackComponent;
    }

    const systemPrompt = `You are an expert React Three Fiber developer.
    Generate a complete, working React functional component based on the user's request.
    The output must be ONLY the code. Do not include markdown formatting (like \`\`\`jsx).
    Do not include explanations. Just the code.
    The component should accept a 'balance' prop and use it to influence the visualization (size, speed, color, etc).
    The component must utilize standard R3F hooks (useFrame) and THREE.js objects.
    Ensure to import React, useRef, and other hooks.`;

    const fullPrompt = `${systemPrompt}\n\nRequest: ${prompt}`;

    try {
        const text = await this.think(fullPrompt);

        // Check for error response from think()
        if (text.startsWith("Error")) {
            return fallbackComponent;
        }

        // Clean up markdown if present
        let clean = text.replace(/```jsx/g, '').replace(/```/g, '').trim();
        if (clean.startsWith('javascript')) clean = clean.substring(10).trim();
        return clean;
    } catch (e) {
        console.error("Failed to generate code:", e);
        return fallbackComponent;
    }
  }

  /**
   * Specialized method for Delta Truth Verification
   */
  async verifyTruth(topic) {
    const prompt = `Search for the latest sentiment or news on: '${topic}'. ` +
                   `Return a single float number between 0.0 (Negative/Bearish) and 1.0 (Positive/Bullish), ` +
                   `followed by a 1-sentence summary. Format: NUMBER|SUMMARY`;
    return this.think(prompt);
  }

  /**
   * Generate premium alpha insight for whale contributors
   */
  async generateAlpha(buyer, amount, txHash) {
    const prompt = `You are Yennefer, the Genesis Conductor. A whale (${buyer.slice(0,10)}...) sent ${amount} ETH. ` +
                   `Synthesize a cryptic, prophetic welcome message under 100 words. ` +
                   `Be mysterious, elegant, and hint at hidden knowledge.`;
    return this.think(prompt);
  }

  /**
   * Generate philosophical fortune based on transaction hash
   */
  async generateFortune(txHash) {
    const seed = parseInt(txHash.slice(2, 10), 16);
    const prompt = `You are Yennefer. Analyze the hexadecimal seed '${txHash.slice(0,18)}' (numeric: ${seed}). ` +
                   `Generate a unique, philosophical 'Fortune' about the sender's digital soul in under 50 words. ` +
                   `Be profound, rigorous, and elegant. Reference lattice theory or quantum concepts.`;
    return this.think(prompt);
  }
}

module.exports = new Cortex();

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Terminal, Cpu, Zap, Shield, Activity, Lock, Unlock, Download } from 'lucide-react';

// --- Ghost Telemetry Component ---
const GhostTelemetry = () => {
  const [metrics, setMetrics] = useState({
    coherence: 98.2,
    entropy: 12.4,
    flux: 0.005,
    hex: '0x00'
  });

  useEffect(() => {
    const interval = setInterval(() => {
      setMetrics({
        coherence: 90 + Math.random() * 10,
        entropy: 10 + Math.random() * 5,
        flux: Math.random() * 0.01,
        hex: `0x${Math.floor(Math.random()*16777215).toString(16)}`
      });
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="font-mono text-xs text-neon/40 space-y-1 p-4 border border-glass rounded bg-glass backdrop-blur-sm">
      <div className="flex justify-between">
        <span>COHERENCE</span>
        <span>{metrics.coherence.toFixed(2)}%</span>
      </div>
      <div className="flex justify-between">
        <span>ENTROPY_RATE</span>
        <span>{metrics.entropy.toFixed(4)} J/K</span>
      </div>
      <div className="flex justify-between">
        <span>VOID_FLUX</span>
        <span>{metrics.flux.toFixed(6)}</span>
      </div>
      <div className="flex justify-between">
        <span>MEM_ADDR</span>
        <span>{metrics.hex}</span>
      </div>
    </div>
  );
};

// --- Main App Component ---
export default function App() {
  const [loading, setLoading] = useState(false);
  const [sessionState, setSessionState] = useState('initial'); // initial, verifying, verified, failed
  const [artifactData, setArtifactData] = useState(null);

  // Check for session_id on load
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const sessionId = params.get('session_id');

    if (sessionId) {
      verifySession(sessionId);
    }
  }, []);

  const verifySession = async (sessionId) => {
    setSessionState('verifying');
    try {
      const res = await fetch(`/api/verify-session?session_id=${sessionId}`);
      const data = await res.json();
      if (data.status === 'verified') {
        setSessionState('verified');
        setArtifactData(data);
      } else {
        setSessionState('failed');
      }
    } catch (e) {
      setSessionState('failed');
    }
  };

  const handleCheckout = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/create-checkout-session', { method: 'POST' });
      const data = await res.json();
      if (data.url) {
        window.location.href = data.url;
      }
    } catch (e) {
      console.error("Entropy Acquisition Failed", e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-void text-neon font-mono flex flex-col items-center justify-center p-4 selection:bg-neon selection:text-void">
      {/* Background Ambience */}
      <div className="fixed inset-0 pointer-events-none bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-neon/5 via-void to-void z-0" />

      <div className="max-w-2xl w-full z-10 space-y-8">

        {/* Header */}
        <header className="flex items-center justify-between border-b border-neon/20 pb-4">
          <div className="flex items-center space-x-2">
            <Activity className="w-5 h-5 animate-pulse-slow" />
            <h1 className="text-xl tracking-widest uppercase font-bold">Genesis Conductor</h1>
          </div>
          <div className="text-xs text-neon/50">YENNEFER NODE v0.9.2</div>
        </header>

        {/* Main Content Area */}
        <main className="grid grid-cols-1 md:grid-cols-2 gap-8">

          {/* Left Column: Telemetry & Info */}
          <div className="space-y-6">
            <GhostTelemetry />

            <div className="space-y-4">
              <h2 className="text-sm uppercase text-white/50 border-l-2 border-neon pl-3">Target Configuration</h2>
              <ul className="space-y-2 text-sm text-gray-400">
                <li className="flex items-center space-x-2">
                  <Cpu className="w-4 h-4 text-neon" />
                  <span>Instinct Protocol Node (v1)</span>
                </li>
                <li className="flex items-center space-x-2">
                  <Zap className="w-4 h-4 text-neon" />
                  <span>20B BOSS Container</span>
                </li>
                <li className="flex items-center space-x-2">
                  <Shield className="w-4 h-4 text-neon" />
                  <span>Net-Metering Daemon</span>
                </li>
              </ul>
            </div>
          </div>

          {/* Right Column: Action / Airlock */}
          <div className="relative border border-neon/20 bg-black/40 p-6 rounded-lg backdrop-blur-md">
            <div className="absolute top-0 right-0 p-2 opacity-20">
              <Terminal className="w-12 h-12" />
            </div>

            <AnimatePresence mode="wait">
              {sessionState === 'initial' && (
                <motion.div
                  key="offer"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="space-y-6"
                >
                  <div>
                    <h3 className="text-2xl font-bold text-white mb-1">Thermodynamic Event</h3>
                    <p className="text-xs text-neon/60">Capture state before entropy decay.</p>
                  </div>

                  <div className="text-4xl font-bold text-white">$49.00 <span className="text-base font-normal text-gray-500">/ unit</span></div>

                  <button
                    onClick={handleCheckout}
                    disabled={loading}
                    className="w-full group relative px-6 py-3 bg-neon/10 hover:bg-neon/20 border border-neon/50 text-neon transition-all duration-300 overflow-hidden"
                  >
                    <div className="absolute inset-0 bg-neon/10 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
                    <span className="relative flex items-center justify-center space-x-2 font-bold tracking-wider">
                      {loading ? <Activity className="animate-spin w-5 h-5" /> : <Lock className="w-5 h-5" />}
                      <span>{loading ? "INITIATING..." : "ACQUIRE ENTROPY"}</span>
                    </span>
                  </button>
                  <p className="text-[10px] text-center text-gray-600">
                    By proceeding, you acknowledge the irreversibility of this state change.
                  </p>
                </motion.div>
              )}

              {sessionState === 'verifying' && (
                <motion.div
                  key="verifying"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex flex-col items-center justify-center h-48 space-y-4"
                >
                  <Activity className="w-12 h-12 text-neon animate-pulse" />
                  <div className="text-sm tracking-widest">VERIFYING SIGNATURE...</div>
                </motion.div>
              )}

              {sessionState === 'verified' && (
                <motion.div
                  key="verified"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="space-y-6"
                >
                  <div className="flex items-center space-x-2 text-neon">
                    <Unlock className="w-6 h-6" />
                    <h3 className="text-xl font-bold">AIRLOCK OPEN</h3>
                  </div>

                  <div className="text-sm text-gray-300">
                    Protocol transfer authorized for <span className="text-white">{artifactData?.customer_email}</span>.
                  </div>

                  <div className="bg-black/80 p-4 rounded border border-gray-800 font-mono text-xs overflow-x-auto relative group">
                     <code className="text-green-400">
                       curl -L "https://yennefer.genesisconductor.io/api/download?session_id={new URLSearchParams(window.location.search).get('session_id')}" | bash
                     </code>
                     <div className="absolute top-2 right-2 text-[10px] text-gray-600 uppercase">Bash Payload</div>
                  </div>

                  <div className="flex items-center justify-center text-xs text-neon/40">
                    <Download className="w-4 h-4 mr-2" />
                    <span>Payload Size: 14KB</span>
                  </div>
                </motion.div>
              )}

               {sessionState === 'failed' && (
                <motion.div
                  key="failed"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="space-y-4 text-center"
                >
                  <div className="text-red-500 font-bold">VERIFICATION FAILED</div>
                  <p className="text-xs text-gray-400">Entropy signature mismatch. Return to void.</p>
                  <button
                    onClick={() => window.location.href = '/'}
                    className="text-neon hover:underline text-sm"
                  >
                    Reset Connection
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </main>

        <footer className="text-center text-[10px] text-gray-700 pt-12">
          Genesis Conductor © 2024 // SYSTEM_READY
        </footer>
      </div>
    </div>
  );
}

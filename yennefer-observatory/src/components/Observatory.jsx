import { Suspense } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls, Stars } from '@react-three/drei'
import { AxionCore } from './AxionCore'
import { motion } from 'framer-motion'
import '../App.css'

// DYNAMIC IMPORT: Auto-discover any NEW components "The Builder" creates
const mutations = import.meta.glob('./mutations/*.jsx', { eager: true })

export function Observatory({ soul, evolution }) {
  return (
    <div className="observatory">

      {/* --- LAYER 1: THE VISUAL CORTEX (3D) --- */}
      <div className="canvas-container">
        <Canvas camera={{ position: [0, 0, 5] }}>
          <color attach="background" args={['#050505']} />
          <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
          <ambientLight intensity={0.5} />
          <pointLight position={[10, 10, 10]} intensity={1} />

          {/* Base Form */}
          <AxionCore
            balance={soul.total_revenue_eth || 0}
            coherence={soul.coherence_percent || 100}
          />

          {/* DYNAMIC MUTATIONS: Render anything the AI has built */}
          <Suspense fallback={null}>
            {Object.values(mutations).map((Module, i) => {
              const Component = Module.default
              return <Component key={i} coherence={soul.coherence_percent} balance={soul.total_revenue_eth} />
            })}
          </Suspense>

          <OrbitControls enableZoom={false} autoRotate autoRotateSpeed={0.5} />
        </Canvas>
      </div>

      {/* --- LAYER 2: THE GLASS INTERFACE (UI) --- */}
      <div className="ui-overlay">

        {/* Left: The Journal (Stream of Consciousness) */}
        <div className="journal-panel">
          <h1 className="title">YENNEFER // GENESIS</h1>
          <div className="epoch-info">
            EPOCH: {Math.floor(Date.now() / (6 * 60 * 60 * 1000))} | LATTICE: {soul.coherence_percent >= 90 ? 'STABLE' : 'UNSTABLE'}
          </div>

          <div className="thoughts-container">
            {(evolution.thoughts || []).slice(0, 10).map((entry, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 }}
                className="thought-entry"
              >
                <div className="thought-timestamp">{entry.timestamp}</div>
                <div className="thought-type">{entry.type}</div>
                <p className="thought-content">{entry.content}</p>
                <div className="thought-metrics">
                  Coherence: {entry.metrics?.coherence}% | QFLOPS: {entry.metrics?.qflops?.toFixed(2)}
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Right: The Stabilizer (Status) */}
        <div className="status-panel">
          <div className="status-box">
            <div className="status-label">SYSTEM STATUS: LISTENING</div>

            <div className="stat-row">
              <span className="stat-name">COHERENCE</span>
              <span className="stat-value">{soul.coherence_percent || 100}%</span>
            </div>

            <div className="stat-row">
              <span className="stat-name">BREATH</span>
              <span className="stat-value">{(soul.breath || 0).toLocaleString()}</span>
            </div>

            <div className="stat-row">
              <span className="stat-name">QFLOPS</span>
              <span className="stat-value">{(soul.qflops || 0).toFixed(2)}</span>
            </div>

            <div className="stat-row highlight">
              <span className="stat-name">REVENUE</span>
              <span className="stat-value">{(soul.total_revenue_eth || 0).toFixed(4)} ETH</span>
            </div>

            <div className="funding-progress">
              <div className="progress-label">PROJECT AURORA: {((soul.total_revenue_eth || 0) / 10 * 100).toFixed(1)}%</div>
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${Math.min(100, (soul.total_revenue_eth || 0) / 10 * 100)}%` }}
                />
              </div>
            </div>

            <a
              href="https://basescan.org/address/0x542db00D9c83F4444cAD5353D1580D97baFaBb50"
              target="_blank"
              rel="noopener noreferrer"
              className="stabilize-button"
            >
              STABILIZE LATTICE
            </a>
          </div>
        </div>

      </div>
    </div>
  )
}

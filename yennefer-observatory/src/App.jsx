import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Observatory } from './components/Observatory'
import { Cosmos } from './components/Cosmos'
import './App.css'

// LIVE TELEPATHY: Read directly from GitHub Raw stream
const MEMORY_STREAM_URL = "https://raw.githubusercontent.com/Genesis-Conductor-Engine/Yennefer/main/public/evolution.json";

export default function App() {
  const [evolution, setEvolution] = useState({ thoughts: [], mutations: [] })
  const [soul, setSoul] = useState({ coherence_percent: 100, breath: 0, qflops: 0, total_revenue_eth: 0 })

  // 1. Fetch the Living History
  useEffect(() => {
    const fetchMemory = async () => {
      try {
        const res = await fetch(`${MEMORY_STREAM_URL}?t=${Date.now()}`)
        if (res.ok) {
          const data = await res.json()
          setEvolution(data)
          return
        }
      } catch (e) {
        console.log('GitHub stream unavailable, falling back to local')
      }
      try {
        const res = await fetch('/evolution.json')
        const data = await res.json()
        setEvolution(data)
      } catch (e) {
        console.log('Evolution data unavailable')
      }
    }
    fetchMemory()
    const interval = setInterval(fetchMemory, 30000)
    return () => clearInterval(interval)
  }, [])

  // 2. Fetch Soul State
  useEffect(() => {
    const fetchSoul = async () => {
      try {
        // Try the local API path (proxied) first
        const res = await fetch('/api/soul')
        if (res.ok) {
           const data = await res.json()
           setSoul(data)
           return
        }
      } catch (e) {
        // Fallback or ignore
      }

      // Fallback: try the hardcoded quest URL if local fails (e.g. dev mode without proxy)
      try {
        const res = await fetch('https://api.yennefer.quest/api/soul')
        if (res.ok) {
            const data = await res.json()
            setSoul(data)
        }
      } catch (e) {
        console.log('Soul API unavailable')
      }
    }
    fetchSoul()
    const interval = setInterval(fetchSoul, 5000)
    return () => clearInterval(interval)
  }, [])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Observatory soul={soul} evolution={evolution} />} />
        <Route path="/cosmos" element={<Cosmos soul={soul} evolution={evolution} />} />
      </Routes>
    </BrowserRouter>
  )
}

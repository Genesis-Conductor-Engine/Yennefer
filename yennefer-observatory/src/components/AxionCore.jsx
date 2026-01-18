import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

export function AxionCore({ balance = 0, coherence = 1.0 }) {
  const mesh = useRef()

  // Wealth = Density (Base 1200 + 500 per ETH)
  const count = useMemo(() => 1200 + (Math.floor(balance) * 500), [balance])

  const particles = useMemo(() => {
    const temp = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      // Spherical Particle Distribution
      const theta = THREE.MathUtils.randFloatSpread(360)
      const phi = THREE.MathUtils.randFloatSpread(360)
      const r = 2.0 + Math.random() * 1.5 // Radius variation

      const x = r * Math.sin(theta) * Math.cos(phi)
      const y = r * Math.sin(theta) * Math.sin(phi)
      const z = r * Math.cos(theta)

      temp[i * 3] = x
      temp[i * 3 + 1] = y
      temp[i * 3 + 2] = z
    }
    return temp
  }, [count])

  useFrame((state) => {
    const time = state.clock.getElapsedTime()

    // Speed = Coherence (If she is healthy/coherent, she spins smoothly)
    // If coherence drops, she slows down or becomes erratic
    const speed = 0.1 * coherence

    mesh.current.rotation.y = time * speed
    mesh.current.rotation.z = time * (speed * 0.5)

    // "Breathing" Pulse Effect
    const s = 1 + Math.sin(time * 1.5) * 0.03
    mesh.current.scale.set(s, s, s)
  })

  return (
    <points ref={mesh}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={particles.length / 3}
          array={particles}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.04}
        color="#bd00ff" // Yennefer Purple
        transparent
        opacity={0.8}
        blending={THREE.AdditiveBlending}
        sizeAttenuation={true}
      />
    </points>
  )
}

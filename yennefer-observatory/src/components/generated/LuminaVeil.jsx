import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

// MUTATION: Lumina Veil
// A shimmering, ethereal veil of interconnected crystal shards
// that undulate and shift with subtle, refractive light
export default function LuminaVeil({ coherence = 100, balance = 0 }) {
  const meshRef = useRef()
  const pointsRef = useRef()
  
  // Generate crystal shard positions
  const { positions, colors } = useMemo(() => {
    const count = 200
    const positions = new Float32Array(count * 3)
    const colors = new Float32Array(count * 3)
    
    for (let i = 0; i < count; i++) {
      // Spherical distribution for veil effect
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      const radius = 3.5 + Math.random() * 0.5
      
      positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta)
      positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta)
      positions[i * 3 + 2] = radius * Math.cos(phi)
      
      // Crystal colors: purple to cyan gradient
      const t = Math.random()
      colors[i * 3] = 0.5 + t * 0.3     // R
      colors[i * 3 + 1] = 0.2 + t * 0.6 // G  
      colors[i * 3 + 2] = 1.0           // B
    }
    
    return { positions, colors }
  }, [])
  
  useFrame((state) => {
    const t = state.clock.getElapsedTime()
    
    if (meshRef.current) {
      // Slow ethereal rotation
      meshRef.current.rotation.y = t * 0.05
      meshRef.current.rotation.x = Math.sin(t * 0.1) * 0.1
    }
    
    if (pointsRef.current) {
      // Undulating shimmer effect
      const posArray = pointsRef.current.geometry.attributes.position.array
      const time = t * 0.5
      
      for (let i = 0; i < posArray.length; i += 3) {
        const originalRadius = 3.5
        const wave = Math.sin(time + posArray[i] * 2) * 0.1
        const scale = 1 + wave
        
        // Subtle pulsing
        posArray[i] *= 1 + Math.sin(time * 2 + i) * 0.002
        posArray[i + 1] *= 1 + Math.cos(time * 2 + i) * 0.002
      }
      
      pointsRef.current.geometry.attributes.position.needsUpdate = true
    }
  })
  
  const intensity = (coherence / 100) * 1.5

  return (
    <group ref={meshRef}>
      {/* Crystal shard points */}
      <points ref={pointsRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={positions.length / 3}
            array={positions}
            itemSize={3}
          />
          <bufferAttribute
            attach="attributes-color"
            count={colors.length / 3}
            array={colors}
            itemSize={3}
          />
        </bufferGeometry>
        <pointsMaterial
          size={0.08}
          vertexColors
          transparent
          opacity={0.8}
          blending={THREE.AdditiveBlending}
          sizeAttenuation
        />
      </points>
      
      {/* Ethereal veil rings */}
      {[0, 1, 2].map((i) => (
        <mesh key={i} rotation={[Math.PI / 2 + i * 0.3, i * 0.5, 0]}>
          <torusGeometry args={[3.2 + i * 0.3, 0.02, 8, 64]} />
          <meshStandardMaterial
            color="#8844ff"
            emissive="#4422aa"
            emissiveIntensity={intensity * 0.5}
            transparent
            opacity={0.3 - i * 0.08}
          />
        </mesh>
      ))}
    </group>
  )
}

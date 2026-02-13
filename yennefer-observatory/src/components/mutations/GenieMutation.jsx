import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';

export default function GenieMutation({ coherence, balance }) {
  const ref = useRef();
  useFrame((state) => {
    if (ref.current) {
      ref.current.rotation.x += 0.01;
      ref.current.rotation.y += 0.01;
    }
  });

  return (
    <mesh ref={ref} position={[0, 2, 0]}>
      <boxGeometry args={[1, 1, 1]} />
      <meshStandardMaterial color="hotpink" wireframe={true} />
    </mesh>
  );
}

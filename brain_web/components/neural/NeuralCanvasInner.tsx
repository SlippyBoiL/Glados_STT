"use client";

import { Canvas } from "@react-three/fiber";
import { OrbitControls, Stars } from "@react-three/drei";
import { NeuralBrainScene } from "./NeuralBrainScene";
import type { ClusterActivity } from "@/lib/neuralState";

export default function NeuralCanvasInner({
  activity,
}: {
  activity: ClusterActivity;
}) {
  return (
    <Canvas
      camera={{ position: [0, 1.2, 9.5], fov: 45 }}
      dpr={[1, 1.75]}
      gl={{ antialias: true, alpha: true }}
      className="h-full w-full"
    >
      <color attach="background" args={["#00050b"]} />
      <fog attach="fog" args={["#00050b", 12, 28]} />
      <ambientLight intensity={0.25} />
      <pointLight position={[6, 8, 4]} intensity={1.2} color="#00F0FF" />
      <pointLight position={[-5, -3, -4]} intensity={0.6} color="#3D7AFF" />
      <Stars radius={60} depth={40} count={1800} factor={2.5} saturation={0} fade speed={0.4} />
      <NeuralBrainScene activity={activity} />
      <OrbitControls
        enablePan={false}
        enableZoom
        autoRotate
        autoRotateSpeed={0.45}
        minDistance={5}
        maxDistance={16}
      />
    </Canvas>
  );
}

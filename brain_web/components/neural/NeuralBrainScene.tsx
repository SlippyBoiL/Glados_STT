"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Line, Sphere, Text } from "@react-three/drei";
import * as THREE from "three";
import {
  NEURAL_CLUSTERS,
  type ClusterActivity,
  type NeuralClusterId,
} from "@/lib/neuralState";

type NeuronSpec = {
  id: string;
  cluster: NeuralClusterId;
  position: [number, number, number];
};

function seededRandom(seed: number) {
  const x = Math.sin(seed * 12.9898) * 43758.5453;
  return x - Math.floor(x);
}

function buildNeurons(countPerCluster = 14): NeuronSpec[] {
  const neurons: NeuronSpec[] = [];
  NEURAL_CLUSTERS.forEach((cluster, ci) => {
    for (let i = 0; i < countPerCluster; i++) {
      const u = seededRandom(ci * 100 + i * 3.1);
      const v = seededRandom(ci * 100 + i * 7.7);
      const w = seededRandom(ci * 100 + i * 11.3);
      const theta = u * Math.PI * 2;
      const phi = Math.acos(2 * v - 1);
      const r = cluster.radius * (0.35 + 0.65 * w);
      const x = cluster.center[0] + r * Math.sin(phi) * Math.cos(theta);
      const y = cluster.center[1] + r * Math.sin(phi) * Math.sin(theta);
      const z = cluster.center[2] + r * Math.cos(phi);
      neurons.push({
        id: `${cluster.id}-${i}`,
        cluster: cluster.id,
        position: [x, y, z],
      });
    }
  });
  return neurons;
}

function NeuronMesh({
  position,
  color,
  active,
  intensity,
  flicker = false,
}: {
  position: [number, number, number];
  color: string;
  active: boolean;
  intensity: number;
  flicker?: boolean;
}) {
  const ref = useRef<THREE.Mesh>(null);
  const matRef = useRef<THREE.MeshStandardMaterial>(null);
  useFrame(({ clock }) => {
    if (!ref.current) return;
    const t = clock.getElapsedTime();
    let inten = intensity;
    if (flicker && intensity > 0.25) {
      inten = intensity * (0.55 + 0.45 * Math.sin(t * 14 + position[0] * 5));
    }
    const pulse = active
      ? 0.08 + 0.12 * Math.sin(t * (6 + inten * 10) + position[0])
      : 0.02 * Math.sin(t * 1.2 + position[1]);
    const s = 1 + pulse * (0.5 + inten);
    ref.current.scale.setScalar(s);
    if (matRef.current) {
      matRef.current.emissiveIntensity = active ? 1.2 + inten * 2.2 : 0.25;
    }
  });

  return (
    <Sphere ref={ref} args={[0.055 + intensity * 0.04, 12, 12]} position={position}>
      <meshStandardMaterial
        ref={matRef}
        color={active ? color : "#003366"}
        emissive={active ? color : "#001133"}
        emissiveIntensity={active ? 1.2 + intensity * 2.2 : 0.25}
        roughness={0.25}
        metalness={0.55}
        transparent
        opacity={0.85 + intensity * 0.15}
      />
    </Sphere>
  );
}

function Synapse({
  a,
  b,
  active,
  color,
}: {
  a: [number, number, number];
  b: [number, number, number];
  active: boolean;
  color: string;
}) {
  return (
    <Line
      points={[a, b]}
      color={color}
      lineWidth={active ? 1.4 : 0.6}
      transparent
      opacity={active ? 0.55 : 0.08}
    />
  );
}

function ClusterCore({
  center,
  label,
  color,
  intensity,
}: {
  center: [number, number, number];
  label: string;
  color: string;
  intensity: number;
}) {
  const ref = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (!ref.current) return;
    const t = clock.getElapsedTime();
    const s = 1 + intensity * 0.35 + (intensity > 0.2 ? 0.08 * Math.sin(t * 8) : 0);
    ref.current.scale.setScalar(s);
  });

  return (
    <group position={center}>
      <Sphere ref={ref} args={[0.18, 24, 24]}>
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={0.6 + intensity * 2.5}
          transparent
          opacity={0.55 + intensity * 0.35}
          roughness={0.15}
          metalness={0.7}
        />
      </Sphere>
      <Text
        position={[0, 0.42, 0]}
        fontSize={0.14}
        color={color}
        anchorX="center"
        anchorY="middle"
        outlineWidth={0.008}
        outlineColor="#00050b"
      >
        {label}
      </Text>
    </group>
  );
}

export function NeuralBrainScene({ activity }: { activity: ClusterActivity }) {
  const neurons = useMemo(() => buildNeurons(16), []);
  const colorByCluster = useMemo(() => {
    const m: Record<string, string> = {};
    for (const c of NEURAL_CLUSTERS) m[c.id] = c.color;
    return m;
  }, []);

  const synapses = useMemo(() => {
    const links: {
      a: [number, number, number];
      b: [number, number, number];
      cluster: NeuralClusterId;
    }[] = [];
    // Connect each cluster core to manager + a few neighbors
    const byId = Object.fromEntries(NEURAL_CLUSTERS.map((c) => [c.id, c]));
    for (const c of NEURAL_CLUSTERS) {
      if (c.id === "manager") continue;
      links.push({
        a: c.center,
        b: byId.manager.center,
        cluster: c.id,
      });
    }
    // Intra-cluster sample links
    const byCluster: Record<string, NeuronSpec[]> = {};
    for (const n of neurons) {
      (byCluster[n.cluster] ||= []).push(n);
    }
    for (const [cid, list] of Object.entries(byCluster)) {
      for (let i = 0; i < list.length - 1; i += 3) {
        links.push({
          a: list[i].position,
          b: list[i + 1].position,
          cluster: cid as NeuralClusterId,
        });
      }
    }
    return links;
  }, [neurons]);

  // Ambient flicker for inference while tokens stream
  const inferenceFlicker = activity.inference.intensity;

  return (
    <group>
      <mesh>
        <sphereGeometry args={[4.8, 32, 32]} />
        <meshBasicMaterial
          color="#00F0FF"
          wireframe
          transparent
          opacity={0.03 + inferenceFlicker * 0.04}
        />
      </mesh>

      {NEURAL_CLUSTERS.map((c) => (
        <ClusterCore
          key={c.id}
          center={c.center}
          label={c.label}
          color={c.color}
          intensity={activity[c.id]?.intensity || 0}
        />
      ))}

      {synapses.map((s, i) => {
        const intensity = activity[s.cluster]?.intensity || 0;
        return (
          <Synapse
            key={`syn-${i}`}
            a={s.a}
            b={s.b}
            active={intensity > 0.15}
            color={colorByCluster[s.cluster] || "#00F0FF"}
          />
        );
      })}

      {neurons.map((n) => {
        const intensity = activity[n.cluster]?.intensity || 0;
        const active = intensity > 0.12;
        return (
          <NeuronMesh
            key={n.id}
            position={n.position}
            color={colorByCluster[n.cluster]}
            active={active}
            intensity={intensity}
            flicker={n.cluster === "inference"}
          />
        );
      })}
    </group>
  );
}

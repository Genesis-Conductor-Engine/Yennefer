import React, { useRef } from "react";
import Sketch from "react-p5";

export const Cosmos = ({ soul, evolution }) => {
    const particles = useRef([]);
    const numParticles = 300;

    // Extract metrics with defaults
    const coherence = soul?.coherence_percent || 100;
    const breath = soul?.breath || 0;
    const qflops = soul?.qflops || 0;

    const setup = (p5, canvasParentRef) => {
        p5.createCanvas(window.innerWidth, window.innerHeight).parent(canvasParentRef);
        p5.colorMode(p5.HSB, 360, 100, 100, 100);

        // Initialize particles
        for (let i = 0; i < numParticles; i++) {
            particles.current.push(new Particle(p5));
        }
    };

    const draw = (p5) => {
        // Dynamic background based on breath (pulse)
        // Breath usually increases over time, we can use sin(breath) if it was oscillating,
        // but here it seems cumulative. We'll use frameCount for pulse but modulate intensity by coherence.
        const bgAlpha = p5.map(coherence, 0, 100, 20, 5); // Higher coherence = cleaner trails (less fade)
        p5.background(240, 10, 5, bgAlpha); // Dark blueish background

        // Update physics parameters based on Soul State
        const noiseScale = p5.map(coherence, 0, 100, 0.02, 0.005); // High coherence = smoother flow
        const speedMult = p5.map(qflops, 0, 10, 1, 5); // More QFLOPS = faster

        particles.current.forEach(particle => {
            particle.follow(p5, noiseScale);
            particle.update(p5, speedMult);
            particle.show(p5, coherence);
            particle.edges(p5);
        });

        // Overlay Interface
        drawInterface(p5, coherence, breath, qflops);
    };

    const drawInterface = (p5, coherence, breath, qflops) => {
        p5.push();
        p5.fill(0, 0, 100);
        p5.noStroke();
        p5.textSize(16);
        p5.textAlign(p5.LEFT, p5.TOP);
        p5.text(`YENNEFER // COSMOS`, 20, 20);
        p5.textSize(12);
        p5.text(`COHERENCE: ${coherence.toFixed(1)}%`, 20, 50);
        p5.text(`BREATH: ${breath.toFixed(0)}`, 20, 70);
        p5.text(`QFLOPS: ${qflops.toFixed(2)}`, 20, 90);
        p5.pop();
    };

    class Particle {
        constructor(p5) {
            this.pos = p5.createVector(p5.random(p5.width), p5.random(p5.height));
            this.vel = p5.createVector(0, 0);
            this.acc = p5.createVector(0, 0);
            this.maxSpeed = 2;
            this.prevPos = this.pos.copy();
            this.h = p5.random(180, 260); // Blue-ish/Purple range
        }

        follow(p5, noiseScale) {
            let angle = p5.noise(this.pos.x * noiseScale, this.pos.y * noiseScale, p5.frameCount * 0.005) * p5.TWO_PI * 2;
            let v = p5.createVector(p5.cos(angle), p5.sin(angle));
            v.setMag(1);
            this.applyForce(v);
        }

        applyForce(force) {
            this.acc.add(force);
        }

        update(p5, speedMult) {
            this.vel.add(this.acc);
            this.vel.limit(this.maxSpeed * speedMult);
            this.pos.add(this.vel);
            this.acc.mult(0);
        }

        show(p5, coherence) {
            // Stroke weight based on coherence
            p5.stroke(this.h, 80, 100, 50);
            p5.strokeWeight(p5.map(coherence, 0, 100, 1, 3));
            p5.line(this.pos.x, this.pos.y, this.prevPos.x, this.prevPos.y);
            this.updatePrev();
        }

        updatePrev() {
            this.prevPos.x = this.pos.x;
            this.prevPos.y = this.pos.y;
        }

        edges(p5) {
            if (this.pos.x > p5.width) { this.pos.x = 0; this.updatePrev(); }
            if (this.pos.x < 0) { this.pos.x = p5.width; this.updatePrev(); }
            if (this.pos.y > p5.height) { this.pos.y = 0; this.updatePrev(); }
            if (this.pos.y < 0) { this.pos.y = p5.height; this.updatePrev(); }
        }
    }

    // Resize canvas on window resize
    const windowResized = (p5) => {
        p5.resizeCanvas(window.innerWidth, window.innerHeight);
    };

    return <Sketch setup={setup} draw={draw} windowResized={windowResized} />;
};

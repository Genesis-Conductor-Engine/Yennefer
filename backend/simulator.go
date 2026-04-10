package main

import (
	"encoding/json"
	"log"
	"math/rand"
	"os"
	"sync"
	"time"
)

type Simulator struct {
	path  string
	state State
	mu    sync.RWMutex
	rng   *rand.Rand
	stop  chan struct{}
	wg    sync.WaitGroup
}

func NewSimulator(path string) *Simulator {
	s := &Simulator{
		path: path,
		rng:  rand.New(rand.NewSource(time.Now().UnixNano())), //nolint:gosec
		stop: make(chan struct{}),
	}
	s.resetInitialState()
	return s
}

func (s *Simulator) resetInitialState() {
	s.mu.Lock()
	s.state = State{
		Protocol:            "SOUL",
		Version:             "4.0.0-Σ",
		Breath:              0.85,
		SurplusTokens:       420912,
		ThermodynamicYield:  1.24,
		TokensGeneratedPerS: 1420.5,
		CoherencePercent:    98.2,
		ConcaveState:        "Stable",
		DerivativeState:     "Positive",
		GPUUtilization:      74.2,
		Timestamp:           float64(time.Now().Unix()),
		UptimeSeconds:       0,
	}
	snapshot := s.state // capture under lock; write after unlock avoids re-entry
	s.mu.Unlock()
	writeState(s.path, snapshot)
}

func (s *Simulator) Start() {
	s.wg.Add(1)
	go func() {
		defer s.wg.Done()
		ticker := time.NewTicker(800 * time.Millisecond)
		defer ticker.Stop()

		for {
			select {
			case <-s.stop:
				return
			case <-ticker.C:
				s.drift()
				s.flush()
			}
		}
	}()
}

func (s *Simulator) Stop() {
	close(s.stop)
	s.wg.Wait()
}

func (s *Simulator) GetState() State {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.state
}

func (s *Simulator) drift() {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.state.Breath = clamp(s.state.Breath+(s.rng.Float64()-0.5)*0.015, 0, 1)
	s.state.CoherencePercent = clamp(s.state.CoherencePercent+(s.rng.Float64()-0.5)*0.8, 82, 99.8)
	s.state.ThermodynamicYield = clamp(s.state.ThermodynamicYield+(s.rng.Float64()-0.5)*0.008, 1.1, 1.42)
	s.state.TokensGeneratedPerS = clamp(s.state.TokensGeneratedPerS+(s.rng.Float64()-0.5)*12, 1380, 1460)
	s.state.GPUUtilization = clamp(s.state.GPUUtilization+(s.rng.Float64()-0.5)*1.8, 62, 89)
	s.state.SurplusTokens += int64(s.rng.Intn(18))
	s.state.UptimeSeconds += 0.8
	s.state.Timestamp = float64(time.Now().Unix())

	if s.state.CoherencePercent > 97 {
		s.state.ConcaveState = "Hyperstable"
	} else if s.state.CoherencePercent < 88 {
		s.state.ConcaveState = "Fracturing"
	} else {
		s.state.ConcaveState = "Stable"
	}
}

// flush snapshots the current state under a read lock and persists it.
func (s *Simulator) flush() {
	s.mu.RLock()
	snapshot := s.state
	s.mu.RUnlock()
	writeState(s.path, snapshot)
}

// writeState marshals st and writes it to path, logging any errors.
// Passing a value (not pointer) ensures the snapshot is immutable by the time
// the marshaller runs, with no further synchronisation required.
func writeState(path string, st State) {
	data, err := json.MarshalIndent(st, "", "  ")
	if err != nil {
		log.Printf("writeState: marshal error: %v", err)
		return
	}
	if err := os.WriteFile(path, data, 0644); err != nil {
		log.Printf("writeState: %v", err)
	}
}

func clamp(v, min, max float64) float64 {
	if v < min {
		return min
	}
	if v > max {
		return max
	}
	return v
}

package main

import (
	"encoding/json"
	"math/rand"
	"os"
	"sync"
	"time"
)

type Simulator struct {
	path  string
	state State
	mu    sync.RWMutex
	stop  chan struct{}
	wg    sync.WaitGroup
}

func NewSimulator(path string) *Simulator {
	s := &Simulator{
		path: path,
		stop: make(chan struct{}),
	}
	s.resetInitialState()
	return s
}

func (s *Simulator) resetInitialState() {
	s.mu.Lock()
	defer s.mu.Unlock()

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
	s.flush()
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

	s.state.Breath = clamp(s.state.Breath+(rand.Float64()-0.5)*0.015, 0, 1)
	s.state.CoherencePercent = clamp(s.state.CoherencePercent+(rand.Float64()-0.5)*0.8, 82, 99.8)
	s.state.ThermodynamicYield = clamp(s.state.ThermodynamicYield+(rand.Float64()-0.5)*0.008, 1.1, 1.42)
	s.state.TokensGeneratedPerS = clamp(s.state.TokensGeneratedPerS+(rand.Float64()-0.5)*12, 1380, 1460)
	s.state.GPUUtilization = clamp(s.state.GPUUtilization+(rand.Float64()-0.5)*1.8, 62, 89)
	s.state.SurplusTokens += int64(rand.Intn(18))
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

func (s *Simulator) flush() {
	data, _ := json.MarshalIndent(s.state, "", "  ")
	os.WriteFile(s.path, data, 0644)
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

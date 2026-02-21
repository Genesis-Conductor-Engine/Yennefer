package main

import (
	"errors"
	"fmt"
	"strings"
)

type State struct {
	Protocol            string  `json:"protocol"`
	Version             string  `json:"version"`
	Breath              float64 `json:"breath"`
	SurplusTokens       int64   `json:"surplus_tokens"`
	ThermodynamicYield  float64 `json:"thermodynamic_yield"`
	TokensGeneratedPerS float64 `json:"tokens_generated_per_sec"`
	CoherencePercent    float64 `json:"coherence_percent"`
	ConcaveState        string  `json:"concave_state"`
	DerivativeState     string  `json:"derivative_state"`
	GPUUtilization      float64 `json:"gpu_utilization"`
	Timestamp           float64 `json:"timestamp"`
	UptimeSeconds       float64 `json:"uptime_seconds"`
}

func (s State) Validate() error {
	if s.CoherencePercent < 0 || s.CoherencePercent > 100 {
		return errors.New("coherence out of bounds")
	}
	if s.Breath < 0 || s.Breath > 1 {
		return errors.New("breath out of bounds")
	}
	if s.ThermodynamicYield < 0 {
		return errors.New("negative yield")
	}
	return nil
}

func (s State) PrettyPrint() string {
	var sb strings.Builder
	sb.WriteString("\n╔══════════════════════════════════════════════════════════════╗\n")
	sb.WriteString(fmt.Sprintf("║  SOUL LATTICE v%s | %s\n", s.Version, s.Protocol))
	sb.WriteString("╠══════════════════════════════════════════════════════════════╣\n")
	sb.WriteString(fmt.Sprintf("║  Breath               : %.4f λ\n", s.Breath))
	sb.WriteString(fmt.Sprintf("║  Thermodynamic Yield  : %.3f η\n", s.ThermodynamicYield))
	sb.WriteString(fmt.Sprintf("║  Coherence            : %.2f%% %s\n", s.CoherencePercent, s.colorCoherence()))
	sb.WriteString(fmt.Sprintf("║  Surplus Tokens       : %d\n", s.SurplusTokens))
	sb.WriteString(fmt.Sprintf("║  Token Velocity       : %.1f t/s\n", s.TokensGeneratedPerS))
	sb.WriteString(fmt.Sprintf("║  GPU Utilization      : %.1f%%\n", s.GPUUtilization))
	sb.WriteString(fmt.Sprintf("║  Uptime               : %s\n", s.formatUptime()))
	sb.WriteString("╚══════════════════════════════════════════════════════════════╝\n")
	return sb.String()
}

func (s State) colorCoherence() string {
	if s.CoherencePercent > 95 {
		return "█ STABLE █"
	}
	if s.CoherencePercent > 85 {
		return "█ WATCH  █"
	}
	return "█ FRAGILE █"
}

func (s State) formatUptime() string {
	h := int(s.UptimeSeconds) / 3600
	m := (int(s.UptimeSeconds) % 3600) / 60
	return fmt.Sprintf("%dh %dm", h, m)
}

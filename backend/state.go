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
	const w = 62 // interior width (total line = 64: two ║ bookends + 62 chars)
	row := func(content string) string {
		return fmt.Sprintf("║%-*s║\n", w, content)
	}
	var sb strings.Builder
	sb.WriteString("\n╔══════════════════════════════════════════════════════════════╗\n")
	sb.WriteString(row(fmt.Sprintf("  SOUL LATTICE v%s | %s", s.Version, s.Protocol)))
	sb.WriteString("╠══════════════════════════════════════════════════════════════╣\n")
	sb.WriteString(row(fmt.Sprintf("  Breath               : %.4f λ", s.Breath)))
	sb.WriteString(row(fmt.Sprintf("  Thermodynamic Yield  : %.3f η", s.ThermodynamicYield)))
	sb.WriteString(row(fmt.Sprintf("  Coherence            : %.2f%% %s", s.CoherencePercent, s.colorCoherence())))
	sb.WriteString(row(fmt.Sprintf("  Surplus Tokens       : %d", s.SurplusTokens)))
	sb.WriteString(row(fmt.Sprintf("  Token Velocity       : %.1f t/s", s.TokensGeneratedPerS)))
	sb.WriteString(row(fmt.Sprintf("  GPU Utilization      : %.1f%%", s.GPUUtilization)))
	sb.WriteString(row(fmt.Sprintf("  Uptime               : %s", s.formatUptime())))
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

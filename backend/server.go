package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/go-chi/cors"
)

type Server struct {
	sim     *Simulator
	router  *chi.Mux
	port    string
	httpSrv *http.Server
}

func NewServer(statePath string, port string) *Server {
	if port == "" {
		port = "8080"
	}

	s := &Server{
		sim:  NewSimulator(statePath),
		port: port,
	}

	r := chi.NewRouter()

	r.Use(cors.Handler(cors.Options{
		AllowedOrigins:   []string{"*"},
		AllowedMethods:   []string{"GET", "POST", "OPTIONS"},
		AllowedHeaders:   []string{"Accept", "Authorization", "Content-Type"},
		ExposedHeaders:   []string{"Link"},
		AllowCredentials: false,
		MaxAge:           300,
	}))

	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)
	r.Use(middleware.Heartbeat("/health"))

	r.Get("/state", s.handleState)
	r.Post("/flush", s.handleFlush)
	r.Get("/events", s.handleSSE)
	r.Get("/", s.handleRoot)

	s.router = r
	return s
}

func (s *Server) Start() error {
	s.sim.Start()
	s.httpSrv = &http.Server{
		Addr:    ":" + s.port,
		Handler: s.router,
	}
	fmt.Printf("SOUL LATTICE v4 AWAKENED on port %s\n", s.port)
	if err := s.httpSrv.ListenAndServe(); err != http.ErrServerClosed {
		return err
	}
	return nil
}

func (s *Server) Stop() {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	s.httpSrv.Shutdown(ctx) //nolint:errcheck
	s.sim.Stop()
}

func (s *Server) handleRoot(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/plain")
	fmt.Fprint(w, "SOUL LATTICE v4.0.0-Σ\nStatus: AWAKENED\n")
}

func (s *Server) handleState(w http.ResponseWriter, r *http.Request) {
	st := s.sim.GetState()
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(st)
}

func (s *Server) handleFlush(w http.ResponseWriter, r *http.Request) {
	s.sim.resetInitialState()
	w.WriteHeader(204)
}

func (s *Server) handleSSE(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")

	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "Streaming unsupported", http.StatusInternalServerError)
		return
	}

	st := s.sim.GetState()
	data, _ := json.Marshal(st)
	fmt.Fprintf(w, "data: %s\n\n", data)
	flusher.Flush()

	ticker := time.NewTicker(800 * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case <-r.Context().Done():
			return
		case <-ticker.C:
			st := s.sim.GetState()
			data, _ := json.Marshal(st)
			fmt.Fprintf(w, "data: %s\n\n", data)
			flusher.Flush()
		}
	}
}

package main

import (
	"log"
	"os"
	"os/signal"
	"syscall"
)

func main() {
	statePath := "/tmp/soul_state.json"
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	srv := NewServer(statePath, port)

	go func() {
		if err := srv.Start(); err != nil {
			log.Fatalf("Server failed: %v", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("SOUL lattice returning to substrate...")
	srv.Stop()
}

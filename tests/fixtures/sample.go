package main

import "fmt"

func greet(name string) {
	fmt.Println("Hello " + name)
}

type Server struct {
	Host string
	Port int
}

func main() {
	greet("world")
}

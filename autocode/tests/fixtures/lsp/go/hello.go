package main

func localAdd(left int, right int) int {
	return left + right
}

func main() {
	_ = localAdd(1, "two")
}

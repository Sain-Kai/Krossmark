package com.krossmark.backend

import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication

@SpringBootApplication
class KrossmarkBackendApplication

fun main(args: Array<String>) {
	runApplication<KrossmarkBackendApplication>(*args)
}

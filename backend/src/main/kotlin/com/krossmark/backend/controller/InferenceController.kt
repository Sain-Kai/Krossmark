package com.krossmark.backend.controller

import com.krossmark.backend.dto.EncryptedPayload
import com.krossmark.backend.dto.PerceptionResult
import com.krossmark.backend.service.CryptoService
import com.krossmark.backend.service.InferenceService
import org.springframework.web.bind.annotation.*
import tools.jackson.databind.ObjectMapper

@RestController
@RequestMapping("/api/inference")
class InferenceController(
    private val cryptoService: CryptoService,
    private val inferenceService: InferenceService,
    private val mapper: ObjectMapper
) {

    @PostMapping("/result")
    fun receiveEncrypted(@RequestBody payload: EncryptedPayload): String {
        val decryptedBytes = cryptoService.decrypt(payload.iv, payload.ciphertext)
        val json = String(decryptedBytes, Charsets.UTF_8)

        val result = mapper.readValue(json, PerceptionResult::class.java)
        inferenceService.saveResult(result)

        return "OK"
    }
}
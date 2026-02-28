package com.krossmark.backend.service

import org.springframework.beans.factory.annotation.Value
import org.springframework.stereotype.Service
import java.util.Base64
import javax.crypto.Cipher
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

@Service
class CryptoService(
    @Value("\${security.aes.key}") private val keyB64: String
) {
    private val keyBytes = Base64.getDecoder().decode(keyB64)

    fun decrypt(ivB64: String, ciphertextB64: String): ByteArray {
        val iv = Base64.getDecoder().decode(ivB64)
        val ciphertext = Base64.getDecoder().decode(ciphertextB64)

        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        val keySpec = SecretKeySpec(keyBytes, "AES")
        val gcmSpec = GCMParameterSpec(128, iv)

        cipher.init(Cipher.DECRYPT_MODE, keySpec, gcmSpec)
        return cipher.doFinal(ciphertext)
    }
}
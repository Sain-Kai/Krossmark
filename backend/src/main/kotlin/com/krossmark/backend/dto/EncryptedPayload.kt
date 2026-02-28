package com.krossmark.backend.dto

data class EncryptedPayload(
    val iv: String,
    val ciphertext: String
)
package com.krossmark.backend.dto

data class PerceptionResult(
    val person_count: Int,
    val groups: Int,
    val group_intent: String,
    val actors: List<ActorDto>,
    val scene_intent: String,
    val threat_level: Int,
    val confidence: Double
)
package com.krossmark.backend.service

import com.krossmark.backend.dto.PerceptionResult
import com.krossmark.backend.entity.EventEntity
import com.krossmark.backend.repository.EventRepository
import org.springframework.stereotype.Service
import tools.jackson.databind.ObjectMapper

@Service
class InferenceService(
    private val repo: EventRepository,
    private val mapper: ObjectMapper
) {
    fun saveResult(result: PerceptionResult) {
        val json = mapper.writeValueAsString(result)
        val entity = EventEntity(
            payload = json,
            threatLevel = result.threat_level
        )
        repo.save(entity)
    }
}
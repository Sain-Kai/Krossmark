package com.krossmark.backend.entity

import jakarta.persistence.*
import java.time.Instant

@Entity
@Table(name = "events")
class EventEntity(
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    var id: Long? = null,

    @Column(columnDefinition = "TEXT")
    var payload: String,

    var threatLevel: Int,

    var createdAt: Instant = Instant.now()
)
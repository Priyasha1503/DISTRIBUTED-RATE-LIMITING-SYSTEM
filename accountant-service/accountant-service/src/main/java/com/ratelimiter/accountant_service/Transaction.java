package com.ratelimiter.accountant_service;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Data;
import java.time.LocalDateTime;

@Entity
@Table(name = "allowed_requests")
@Data
public class Transaction {
    @Id
    private String transactionId;
    private String clientIp;
    private Long timestamp;
    private LocalDateTime processedAt = LocalDateTime.now();
}
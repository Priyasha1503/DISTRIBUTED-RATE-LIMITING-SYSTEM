package com.ratelimiter.accountant_service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Service;

@Service
public class KafkaConsumerService {

    private final TransactionRepository repository;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public KafkaConsumerService(TransactionRepository repository) {
        this.repository = repository;
    }

    @KafkaListener(topics = "allowed_requests", groupId = "accountant-group")
    public void consume(String message) {
        try {
            // Convert the JSON string from Python into a Java Object
            Transaction txn = objectMapper.readValue(message, Transaction.class);

            // Save to MySQL
            repository.save(txn);

            System.out.println("SAVED TO MYSQL: " + txn.getTransactionId());
        } catch (Exception e) {
            System.err.println("Error processing message: " + e.getMessage());
        }
    }
}
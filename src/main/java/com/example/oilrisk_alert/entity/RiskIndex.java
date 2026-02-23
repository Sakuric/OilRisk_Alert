package com.example.oilrisk_alert.entity;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
public class RiskIndex {
    private Long id;
    private LocalDate date;
    private BigDecimal riskIndex;
    private String riskLevel;
    private BigDecimal oilPrice;
    private LocalDateTime createdAt;
}

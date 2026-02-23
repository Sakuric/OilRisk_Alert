package com.example.oilrisk_alert.entity;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
public class RiskFactor {
    private Long id;
    private LocalDate date;
    private String factorName;
    private String factorNameZh;
    private String category;
    private BigDecimal value;
    private BigDecimal shapValue;
    private LocalDateTime createdAt;
}

package com.example.oilrisk_alert.entity;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
public class Alert {
    private Long id;
    private LocalDate date;
    private String level;
    private BigDecimal riskIndex;
    private String triggerType;
    private String triggerFactor;
    private String triggerFactorZh;
    private String summary;
    private String summaryEn;
    private String detail;
    private String aiReport;
    private LocalDateTime createdAt;
}

package com.example.oilrisk_alert.vo;

import lombok.Data;

import java.math.BigDecimal;

@Data
public class AlertVO {
    private Long id;
    private String date;
    private String level;
    private BigDecimal riskIndex;
    private String triggerType;
    private String triggerFactor;
    private String triggerFactorZh;
    private String summary;
    private String summaryEn;
    private String aiReport;
}

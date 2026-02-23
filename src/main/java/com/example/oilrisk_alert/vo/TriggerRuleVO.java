package com.example.oilrisk_alert.vo;

import lombok.Data;

import java.math.BigDecimal;

@Data
public class TriggerRuleVO {
    private String ruleType;
    private String factor;
    private String factorZh;
    private BigDecimal currentValue;
    private BigDecimal threshold;
    private String description;
}

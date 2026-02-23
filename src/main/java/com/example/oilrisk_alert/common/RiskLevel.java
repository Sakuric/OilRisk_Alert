package com.example.oilrisk_alert.common;

import java.math.BigDecimal;

public enum RiskLevel {

    LOW("Low", BigDecimal.ZERO, new BigDecimal("40")),
    MEDIUM("Medium", new BigDecimal("40"), new BigDecimal("70")),
    HIGH("High", new BigDecimal("70"), new BigDecimal("100"));

    private final String label;
    private final BigDecimal lowerBound; // inclusive
    private final BigDecimal upperBound; // exclusive for Low/Medium, inclusive for High

    RiskLevel(String label, BigDecimal lowerBound, BigDecimal upperBound) {
        this.label = label;
        this.lowerBound = lowerBound;
        this.upperBound = upperBound;
    }

    public String getLabel() {
        return label;
    }

    /**
     * BR-01: Low [0,40), Medium [40,70), High [70,100]
     */
    public static RiskLevel fromIndex(BigDecimal riskIndex) {
        if (riskIndex.compareTo(new BigDecimal("40")) < 0) {
            return LOW;
        } else if (riskIndex.compareTo(new BigDecimal("70")) < 0) {
            return MEDIUM;
        } else {
            return HIGH;
        }
    }
}

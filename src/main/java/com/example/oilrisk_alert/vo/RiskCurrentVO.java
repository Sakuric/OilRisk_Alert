package com.example.oilrisk_alert.vo;

import lombok.Data;

import java.math.BigDecimal;
import java.util.List;

@Data
public class RiskCurrentVO {
    private BigDecimal riskIndex;
    private String riskLevel;
    private String date;
    private List<FactorVO> topFactors;
}

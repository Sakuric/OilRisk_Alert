package com.example.oilrisk_alert.vo;

import lombok.Data;

import java.math.BigDecimal;
import java.util.List;

@Data
public class WeightUpdateResultVO {
    private BigDecimal riskIndex;
    private String riskLevel;
    private List<RadarScoreVO> radarScores;
    private List<FactorVO> topFactors;
}

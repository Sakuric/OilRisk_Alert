package com.example.oilrisk_alert.vo;

import lombok.Data;

import java.math.BigDecimal;
import java.util.List;

@Data
public class RadarScoreVO {
    private String category;
    private String categoryZh;
    private BigDecimal score;
    private List<FactorVO> topFactors;
}

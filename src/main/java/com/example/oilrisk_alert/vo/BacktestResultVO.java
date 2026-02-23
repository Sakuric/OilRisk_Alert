package com.example.oilrisk_alert.vo;

import lombok.Data;

import java.math.BigDecimal;
import java.util.List;

@Data
public class BacktestResultVO {
    private List<String> dates;
    private List<BigDecimal> actual;
    private List<BigDecimal> predicted;
    private BigDecimal hitRate;
    private BigDecimal falseAlarmRate;
    private BigDecimal mae;
    private BigDecimal directionAccuracy;
}

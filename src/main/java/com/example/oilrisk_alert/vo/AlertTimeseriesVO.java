package com.example.oilrisk_alert.vo;

import lombok.Data;

import java.math.BigDecimal;

@Data
public class AlertTimeseriesVO {
    private String date;
    private String level;
    private BigDecimal riskIndex;
}

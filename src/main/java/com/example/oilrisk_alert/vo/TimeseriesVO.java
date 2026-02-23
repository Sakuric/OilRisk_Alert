package com.example.oilrisk_alert.vo;

import lombok.Data;

import java.math.BigDecimal;
import java.util.List;

@Data
public class TimeseriesVO {
    private List<String> dates;
    private List<BigDecimal> oilPrice;
    private List<BigDecimal> riskIndex;
    private List<AlertTimeseriesVO> alerts;
}

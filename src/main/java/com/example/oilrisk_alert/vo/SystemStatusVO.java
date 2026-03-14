package com.example.oilrisk_alert.vo;

import lombok.Data;

import java.util.Map;

@Data
public class SystemStatusVO {
    private String lastCollectionTime;
    private String lastCollectionStatus;
    private String lastPredictionTime;
    private String dataDate;
    private String nextScheduled;
    private Map<String, FactorCoverageVO> factorsCoverage;

    @Data
    public static class FactorCoverageVO {
        private int total;
        private int available;
    }
}

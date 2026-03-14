package com.example.oilrisk_alert.vo;

import lombok.Data;

import java.util.List;
import java.util.Map;

@Data
public class CollectResultVO {
    private String status;
    private String message;
    private CollectionDetail collection;
    private PredictionSummary prediction;

    @Data
    public static class CollectionDetail {
        private String date;
        private int total;
        private int success;
        private int failed;
        private List<String> failedFactors;
        private int durationMs;
    }

    @Data
    public static class PredictionSummary {
        private double score;
        private String level;
        private String date;
    }
}

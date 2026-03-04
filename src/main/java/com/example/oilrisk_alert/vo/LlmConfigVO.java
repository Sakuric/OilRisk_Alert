package com.example.oilrisk_alert.vo;

import lombok.Data;

@Data
public class LlmConfigVO {

    private String providerName;
    private String apiUrl;
    private String apiKey;
    private String model;
}

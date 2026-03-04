package com.example.oilrisk_alert.config;

import lombok.Data;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Data
@Component
public class LlmConfig {

    @Value("${llm.api.url:https://apis.iflow.cn/v1/chat/completions}")
    private String apiUrl;

    @Value("${llm.api.key:}")
    private String apiKey;

    @Value("${llm.api.model:qwen3-max}")
    private String model;

    private String providerName = "iflow";

    public String getMaskedKey() {
        if (apiKey == null || apiKey.length() <= 4) {
            return "****";
        }
        return "*".repeat(apiKey.length() - 4) + apiKey.substring(apiKey.length() - 4);
    }
}
